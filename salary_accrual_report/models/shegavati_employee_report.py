# -*- coding: utf-8 -*-

from odoo import models, fields, _


class ShegavatiEmployeeReport(models.Model):
    _name = 'shegavati.employee.report'
    _description = 'Shegavati Employee Report'

    start_date = fields.Date(string='დაწყების თარიღი', required=True)
    end_date = fields.Date(string='საბოლოო თარიღი', required=True)
    partner_id = fields.Many2one('res.partner', string='თანამშრომელი', required=True, ondelete='cascade')
    total_credits = fields.Float(string='ათვისებული შეღავათი')
    shegavati = fields.Float(string='დარჩენილი შეღავათი')
    partner_shegavati = fields.Float(string='თანამშრომლის შეღავათი')
    partner_vat = fields.Char(related='partner_id.vat')
    total_credits_2 = fields.Float(string='საპენსიოს გარეშე')
    

    def action_view_entries(self):
        self.ensure_one()
        account_3130 = self.env['account.account'].search([('code', '=', '3130')], limit=1)
        if not account_3130:
            return {}
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('move_id.date', '>=', self.start_date),
            ('move_id.date', '<=', self.end_date),
            ('account_id', '=', account_3130.id),
            ('move_id.state', '=', 'posted'),
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items'),
            'res_model': 'account.move.line',
            'view_mode': 'list',
            'domain': domain,
            'context': {'search_default_group_by_partner': 0},
        }

