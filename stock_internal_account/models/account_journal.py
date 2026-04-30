
from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    use_for_stock_reconcile = fields.Boolean(
        string="Use for Stock Reconciliation",
        help="If checked, this journal will be used for stock reconciliation entries."
    )