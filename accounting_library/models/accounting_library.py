from odoo import api, fields, models


class AccountingLibrary(models.Model):
    _name = "accounting.library"
    _description = "Accounting Library"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "document_number"

    category_id = fields.Many2one(
        "accounting.library.category",
        string="კატეგორია",
        required=True,
        tracking=True,
    )
    inspektireba_id = fields.Many2one(
        "inspektireba", string="ინსპექტირება", tracking=True,
    )
    approval_id = fields.Many2one(
        "approval.request", string="მოთხოვნა", tracking=True,
    )
    document_number = fields.Char(
        string="დოკუმენტის ნომერი",
        compute="_compute_document_number",
        store=True,
        tracking=True,
    )
    date = fields.Date(
        string="თარიღი",
        default=fields.Date.context_today,
        tracking=True,
    )
    state = fields.Selection(
        [("sent", "გაგზავნილი"), ("done", "დასრულებული")],
        string="სტატუსი",
        default="sent",
        required=True,
        tracking=True,
    )

    @api.depends(
        "inspektireba_id",
        "inspektireba_id.number",
        "approval_id",
        "approval_id.name",
    )
    def _compute_document_number(self):
        for rec in self:
            if rec.inspektireba_id:
                rec.document_number = rec.inspektireba_id.number
            elif rec.approval_id:
                rec.document_number = rec.approval_id.name
            else:
                rec.document_number = False

    def action_mark_done(self):
        self.write({"state": "done"})

    def action_reset_to_sent(self):
        self.write({"state": "sent"})
