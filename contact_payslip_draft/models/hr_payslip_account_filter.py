from odoo import models, fields

class HrPayslipAccountFilter(models.Model):
    _name = 'hr.payslip.account.filter'
    _description = 'Payroll Partner Assignment Rules'

    name = fields.Char(string="Rule Name", required=True)
    account_ids = fields.Many2many('account.account', string='Target Accounts', required=True)
    category_ids = fields.Many2many('hr.salary.rule.category', string='Salary Rule Categories', required=True)
    partner_id = fields.Many2one('res.partner', string='Fixed Partner',
                                 help="If empty, the system will use the Employee's partner.")
