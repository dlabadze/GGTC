from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrLeavePatch(models.Model):
    _inherit = "hr.leave"

    def _sync_global_sequence(self):
        self.env.cr.execute("SELECT COALESCE(MAX(timeoff_id), 0) FROM hr_leave")
        max_id = self.env.cr.fetchone()[0]
        seq = self.env["ir.sequence"].sudo().search([("code", "=", "hr.leave.global.seq")], limit=1)
        if seq and seq.number_next_actual <= max_id:
            seq.sudo().write({'number_next': max_id + 1})
        return max_id

    @api.model_create_multi
    def create(self, vals_list):
        # Lock to ensure atomic ID assignment across parallel requests
        self.env.cr.execute("LOCK TABLE hr_leave IN SHARE ROW EXCLUSIVE MODE")
        
        # Sync global sequence to prevent "duplicate key" if it drifted
        max_id = self._sync_global_sequence()
        
        # Caches for type-specific sequences within this batch
        type_counters = {}

        for vals in vals_list:
            vals.pop("number_of_days", None)
            
            # 1. Handle Global ID (timeoff_id)
            if not vals.get("timeoff_id"):
                next_val = self.env["ir.sequence"].sudo().next_by_code("hr.leave.global.seq")
                if next_val:
                    vals["timeoff_id"] = int(next_val)
                else:
                    # Fallback if sequence is missing
                    max_id += 1
                    vals["timeoff_id"] = max_id

            # 2. Handle Per-Type Sequence (timeoff_type_seq)
            holiday_status_id = vals.get("holiday_status_id")
            if holiday_status_id and not vals.get("timeoff_type_seq"):
                if holiday_status_id not in type_counters:
                    self.env.cr.execute(
                        "SELECT COALESCE(MAX(timeoff_type_seq), 0) FROM hr_leave WHERE holiday_status_id = %s",
                        (holiday_status_id,),
                    )
                    type_counters[holiday_status_id] = self.env.cr.fetchone()[0]
                
                type_counters[holiday_status_id] += 1
                vals["timeoff_type_seq"] = type_counters[holiday_status_id]

        return super().create(vals_list)

    def write(self, vals):
        vals.pop("number_of_days", None)
        
        # Check if holiday_status_id is changing to re-assign type-specific sequence
        reassign_records = self.env['hr.leave']
        new_type_id = vals.get("holiday_status_id")
        if new_type_id:
            for rec in self:
                if rec.holiday_status_id.id != new_type_id:
                    reassign_records |= rec

        res = super().write(vals)

        if reassign_records:
            self.env.cr.execute("LOCK TABLE hr_leave IN SHARE ROW EXCLUSIVE MODE")
            type_counters = {}
            for rec in reassign_records:
                tid = rec.holiday_status_id.id
                if tid not in type_counters:
                    self.env.cr.execute(
                        "SELECT COALESCE(MAX(timeoff_type_seq), 0) FROM hr_leave WHERE holiday_status_id = %s AND id != %s",
                        (tid, rec.id),
                    )
                    type_counters[tid] = self.env.cr.fetchone()[0]
                
                type_counters[tid] += 1
                new_seq = type_counters[tid]
                
                self.env.cr.execute(
                    "UPDATE hr_leave SET timeoff_type_seq = %s WHERE id = %s",
                    (new_seq, rec.id),
                )
                rec.invalidate_recordset(["timeoff_type_seq"])

        return res
