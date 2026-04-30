from odoo import models, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    contract_num = fields.Char(
        string="კონტრაქტის ნომერი"
    )
