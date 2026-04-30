from odoo import fields, models


class AccountingLibraryCategory(models.Model):
    _name = "accounting.library.category"
    _description = "Accounting Library Category"
    _order = "name"

    name = fields.Char(string="დასახელება", required=True)
