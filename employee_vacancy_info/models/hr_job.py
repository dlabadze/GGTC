from odoo import models, fields, api


class HrJob(models.Model):
    _inherit = 'hr.job'

    vacancy_count = fields.Integer(
        string="ვაკანსიის რაოდენობა",
        compute='_compute_vacancy_count',
        store=True,
        help="Difference between quota (no_of_recruitment) and current employee count (no_of_employee)"
    )

    @api.depends('no_of_recruitment', 'no_of_employee')
    def _compute_vacancy_count(self):
        for job in self:
            quota = job.no_of_recruitment
            current_employees = job.no_of_employee
            job.vacancy_count = quota - current_employees

