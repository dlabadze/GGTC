from odoo import models, fields, api

class ApprovalTableLine(models.Model):
    _name = "approval.table.line.ext"
    _description = "Approvals Second Table"


    line_id = fields.Many2one(
        "approval.table.line",
        string="Approval Line",
        ondelete="cascade",
    )

    request_id = fields.Many2one(
        related="line_id.request_id",
        store=True,
        readonly=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
    )

