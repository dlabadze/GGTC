from odoo import models, fields
from odoo.exceptions import UserError


class JobSalaryUpdateWizard(models.TransientModel):
    _name = 'job.salary.update.wizard'
    _description = 'Bulk Update Expected Salary'

    operation = fields.Selection([
        ('increase', 'გაზრდა'),
        ('decrease', 'შემცირება'),
    ], string="ოპერაცია", required=True)

    percentage = fields.Float(
        string="პროცენტი",
        required=True
    )

    job_ids = fields.Many2many(
        'hr.job',
        string='სამუშაო პოზიციები'
    )

    apply_all = fields.Boolean(
        string='ყველა პოზიცია'
    )

    effective_date = fields.Date(
        string='თარიღი',
        required=True,
        default=fields.Date.context_today
    )

    comment = fields.Text(
        string='კომენტარი'
    )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            res['job_ids'] = [(6, 0, active_ids)]
        return res

    def action_apply(self):
        if self.percentage <= 0:
            raise UserError('პროცენტი უნდა იყოს დადებითი.')

        Job = self.env['hr.job']

        if self.apply_all:
            jobs = Job.search([])
        else:
            if not self.job_ids:
                raise UserError('აირჩიეთ მინიმუმ ერთი სამუშაო პოზიცია.')
            jobs = self.job_ids

        for job in jobs:
            old_salary = job.expected_salary or 0.0

            if self.operation == 'increase':
                new_salary = old_salary * (1 + self.percentage / 100)
            else:
                new_salary = old_salary * (1 - self.percentage / 100)

            job.write({
                'expected_salary': new_salary,
                'date_contract': self.effective_date,
            })

            if self.comment:
                job.message_post(
                    body=(
                        f"<b>Expected Salary Update</b><br/>"
                        f"Operation: {dict(self._fields['operation'].selection).get(self.operation)}<br/>"
                        f"Percentage: {self.percentage}%<br/>"
                        f"Old Salary: {old_salary}<br/>"
                        f"New Salary: {new_salary}<br/>"
                        f"Date: {self.effective_date}<br/>"
                        f"Comment: {self.comment}"
                    )
                )
