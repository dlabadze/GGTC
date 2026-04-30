from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    lines = env['account.payment.line'].search([('budget_line_id', '!=', False)])
    lines._compute_budget_line_display()
