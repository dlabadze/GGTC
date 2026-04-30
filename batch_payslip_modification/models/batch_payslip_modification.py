# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    department_ids = fields.Many2many(
        'hr.department',
        string="Departments",
        domain="[('parent_id', 'child_of', department_id)]"
    )

    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
        compute='_compute_employee_ids', store=True, readonly=False,
        context={'active_test': False}
    )

    def get_employees_domain(self):
        domain = self._get_available_contracts_domain()

        # Explicitly make sure to include archived employees
        domain = expression.AND([
            domain,
            ['|', ('active', '=', False), ('active', '=', True)]
        ])

        # NEW LOGIC: explicit child departments
        if self.department_id and self.department_ids:
            domain = expression.AND([
                domain,
                [('department_id', 'in', self.department_ids.ids)]
            ])

        # FALLBACK: original Odoo behavior
        elif self.department_id:
            domain = expression.AND([
                domain,
                [('department_id', 'child_of', self.department_id.id)]
            ])

        # keep base filters unchanged
        if self.structure_type_id:
            domain = expression.AND([
                domain,
                [('structure_type_id', '=', self.structure_type_id.id)]
            ])

        if self.job_id:
            domain = expression.AND([
                domain,
                [('job_id', '=', self.job_id.id)]
            ])

        if self.structure_id:
            domain = expression.AND([
                domain,
                [('structure_type_id', '=', self.structure_id.type_id.id)]
            ])

        return domain


    @api.depends('structure_id', 'department_id', 'structure_type_id', 'job_id', 'department_ids')
    def _compute_employee_ids(self):
        for wizard in self:
            wizard.employee_ids = self.env['hr.employee'].with_context(active_test=False).search(
                wizard.get_employees_domain()
            )

    def _get_employees(self):
        active_employee_ids = self.env.context.get('active_employee_ids', False)
        if active_employee_ids:
            return self.env['hr.employee'].with_context(active_test=False).browse(active_employee_ids)
        return self.env['hr.employee'].with_context(active_test=False).search(self._get_available_contracts_domain())
