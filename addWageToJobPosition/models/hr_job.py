from odoo import models, api, fields

class HrJob(models.Model):
    _inherit = 'hr.job'

    expected_salary = fields.Monetary(string="ხელფასი")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    date_contract = fields.Date(string="თარიღი")