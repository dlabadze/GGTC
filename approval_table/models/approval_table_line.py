from odoo import models, fields, api

class ApprovalTableLine(models.Model):
    _name = "approval.table.line"
    _description = "Approval Table Line"

    request_id = fields.Many2one("approval.request", string="Approval Request", ondelete="cascade")
    model_id = fields.Many2one("fleet.vehicle.model", string="Model")

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_employee_ext()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if 'x_studio_employee' in vals:
            self._sync_employee_ext()
        return result

    def _sync_employee_ext(self):
        if not self:
            return

        Ext = self.env["approval.table.line.ext"]
        existing = Ext.search([('line_id', 'in', self.ids)])
        existing_map = {ext.line_id.id: ext for ext in existing}

        for line in self:
            ext = existing_map.get(line.id)

            if line.x_studio_employee:
                if ext:
                    ext.write({
                        'employee_id': line.x_studio_employee.id,
                        'request_id': line.request_id.id,
                    })
                else:
                    Ext.create({
                        'line_id': line.id,
                        'employee_id': line.x_studio_employee.id,
                        'request_id': line.request_id.id,
                    })
            elif ext:
                ext.unlink()