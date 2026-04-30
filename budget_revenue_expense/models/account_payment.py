from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    revenue_code = fields.Many2one(
        'account.analytic.account',
        string='Revenue Code',
        help='Revenue analytic account',
        domain="[('plan_id', 'child_of', 2)]"
    )
