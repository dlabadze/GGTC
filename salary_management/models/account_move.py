from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    salary_import_id = fields.Many2one('salary.import', string='Salary Import', readonly=True)