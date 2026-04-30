from odoo import models, fields, api, _

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    leave_manager_id = fields.Many2one(
        'hr.employee',
        string="Leave Manager",
        readonly=True,
    )