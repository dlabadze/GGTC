from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    vacancy_count = fields.Integer(
        string="ვაკანსიის რაოდენობა",
        compute='_compute_vacancy_count',
        store=True,
        help="Difference between x_studio_targetempl and x_studio_currentempl"
    )

    @api.depends('x_studio_targetempl', 'x_studio_currentempl')
    def _compute_vacancy_count(self):
        for emp in self:
            quota = emp.x_studio_targetempl or 0
            current = emp.x_studio_currentempl or 0
            emp.vacancy_count = quota - current
