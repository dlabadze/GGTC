from odoo import models, fields, api


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    total_employee_count = fields.Integer(
        string='Total Employees',
        compute='_compute_total_employee_count'
    )

    @api.depends('employee_ids')
    def _compute_total_employee_count(self):
        for record in self:
            record.total_employee_count = len(record.employee_ids)