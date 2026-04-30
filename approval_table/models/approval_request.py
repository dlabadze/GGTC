from odoo import models, fields

class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    table_line_ids = fields.One2many(
        "approval.table.line",
        "request_id",
        string="Request Table"
    )
    table_line_ext_ids = fields.One2many(
        "approval.table.line.ext",
        "request_id",
        string="Request Table Extension"
    )
