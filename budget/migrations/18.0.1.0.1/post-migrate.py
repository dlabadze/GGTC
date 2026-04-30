from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    from odoo.addons.budget.hooks import create_missing_budget_line_changes
    create_missing_budget_line_changes(env)

