from odoo import models, fields

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    saidentifikacio_code = fields.Char(string='საიდენტიფიკაციო კოდი')

