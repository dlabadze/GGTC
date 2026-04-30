from odoo import models, fields, api, _


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    leave_manager_id = fields.Many2one('res.users', 'Leave Manager')