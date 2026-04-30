# -*- coding: utf-8 -*-

from odoo import models, fields, _


class SalaryAccrualReportWizard(models.TransientModel):
    _name = 'salary.accrual.report.wizard'
    _description = 'Salary Accrual Report Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def action_confirm(self):
        self.ensure_one()
        journal_ids = self.env['account.journal'].search([('name', '=', 'Salaries')], limit=1)
        moves = self.env['account.move'].search([
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
            ('journal_id', 'in', journal_ids.ids),
        ])
        line_ids = moves.mapped('line_ids').ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('ხელფასის დარიცხვის რეპორტი'),
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'view_id': self.env.ref('salary_accrual_report.view_account_move_line_salary_accrual_list').id,
            'domain': [('id', 'in', line_ids)],
            'context': {'search_default_group_by_partner': 1},
        }
