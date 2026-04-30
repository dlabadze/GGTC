from odoo import models, fields, api

class PurchasePlanChanges(models.Model):
    _inherit = "purchase.plan.changes"

    first_line_date = fields.Date(
        string="თარიღი",
        compute="_compute_first_line_fields",
        store=True
    )

    first_line_amount = fields.Float(
        string="თანხა",
        compute="_compute_first_line_fields",
        store=True
    )

    first_line_comment = fields.Text(
        string="კომენტარი",
        compute="_compute_first_line_fields",
        store=True
    )

    @api.depends("line_ids", "line_ids.date", "line_ids.amount")
    def _compute_first_line_fields(self):
        for rec in self:
            first = rec.line_ids[:1]
            if first:
                rec.first_line_date = first.date
                rec.first_line_amount = first.amount
                rec.first_line_comment = first.comment
            else:
                rec.first_line_date = False
                rec.first_line_amount = 0.0
                rec.first_line_comment = ""
