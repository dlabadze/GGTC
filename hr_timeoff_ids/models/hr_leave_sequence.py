from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrLeave(models.Model):
    _inherit = "hr.leave"

    # Global, system-wide unique ID (starts from 1)
    timeoff_id = fields.Integer(
        string="Time Off ID",
        readonly=True,
        copy=False,
        index=True,
        help="Global unique identifier for this Time Off.",
    )

    # Unique per Time Off Type (starts from 1 for each type)
    timeoff_type_seq = fields.Integer(
        string="Time Off Type ID",
        readonly=True,
        copy=False,
        index=True,
        help="Sequential ID within the selected Time Off Type.",
    )

    _sql_constraints = [
        # enforce global uniqueness for timeoff_id
        ("timeoff_id_unique", "unique(timeoff_id)", "Time Off ID must be unique."),
        # enforce uniqueness per type for timeoff_type_seq
        (
            "timeoff_type_seq_unique",
            "unique(holiday_status_id, timeoff_type_seq)",
            "Time Off Type ID must be unique within the selected Time Off Type.",
        ),
    ]

    # @api.model_create_multi
    # def create(self, vals_list):
    #     """Assign IDs on create BEFORE insert to avoid constraint errors."""
    #     seq = self.env.ref("hr_timeoff_ids.seq_hr_leave_global", raise_if_not_found=False)
    #
    #     for vals in vals_list:
    #         # Assign global Time Off ID
    #         if not vals.get("timeoff_id"):
    #             if seq:
    #                 vals["timeoff_id"] = int(self.env["ir.sequence"].next_by_code("hr.leave.global.seq"))
    #             else:
    #                 max_id = self.search([], order="timeoff_id desc", limit=1).timeoff_id or 0
    #                 vals["timeoff_id"] = max_id + 1
    #
    #         # Assign per-type sequential ID
    #         if vals.get("holiday_status_id") and not vals.get("timeoff_type_seq"):
    #             max_type = self.search(
    #                 [("holiday_status_id", "=", vals["holiday_status_id"])],
    #                 order="timeoff_type_seq desc",
    #                 limit=1,
    #             ).timeoff_type_seq or 0
    #             vals["timeoff_type_seq"] = max_type + 1
    #
    #     # Now create with IDs already assigned
    #     return super().create(vals_list)
    #
    # def write(self, vals):
    #     """If Time Off Type changes, reassign the per-type ID for the new type."""
    #     res = super().write(vals)
    #     if "holiday_status_id" in vals:
    #         for rec in self:
    #             if rec.holiday_status_id and self.env.context.get("reassign_type_seq", True):
    #                 max_type = self.search(
    #                     [("holiday_status_id", "=", rec.holiday_status_id.id)],
    #                     order="timeoff_type_seq desc",
    #                     limit=1,
    #                 ).timeoff_type_seq or 0
    #                 rec.with_context(reassign_type_seq=False).timeoff_type_seq = max_type + 1
    #     return res
