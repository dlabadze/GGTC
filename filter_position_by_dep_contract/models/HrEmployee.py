from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    available_job_ids = fields.Many2many(
        'hr.job',
        compute='_compute_available_job_ids',
        string='Available Job Positions',
        store=False
    )

    @api.depends('department_id')
    def _compute_available_job_ids(self):
        for contract in self:
            if contract.department_id:
                contract.available_job_ids = self.env['hr.job'].search([
                    ('department_id', '=', contract.department_id.id)
                ])
            else:
                contract.available_job_ids = self.env['hr.job'].search([])

    @api.onchange('job_id')
    def _onchange_job_id(self):
        if self.job_id and not self.department_id:
            self.department_id = self.job_id.department_id