from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.onchange('job_id', 'department_id')
    def _onchange_job_or_department(self):
        if self.job_id:
            self.wage = self.job_id.expected_salary or 0.0
#x_studio_monetary_field_7gl_1iu13c1vu have to be renamed to expected_salary