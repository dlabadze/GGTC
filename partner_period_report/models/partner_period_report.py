from odoo import models, fields, api, _


class PartnerPeriodReport(models.Model):
    _name = 'partner.period.report'
    _description = 'Partner Period Report'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    account_id = fields.Many2one('account.account', string='Account')
    partner_id = fields.Many2one('res.partner', string='Partner')
    partner = fields.Char(string='Partner Name')
    vat = fields.Char(related='partner_id.vat')
    initial_balance_debit = fields.Float(string='საწყისი ნაშთი დებიტი')
    initial_balance_credit = fields.Float(string='საწყისი ნაშთი კრედიტი')
    brunva_debit = fields.Float(string='ბრუნვა დებიტი')
    brunva_credit = fields.Float(string='ბრუნვა კრედიტი')
    final_balance_debit = fields.Float(string='საბოლოო ნაშთი დებიტი')
    final_balance_credit = fields.Float(string='საბოლოო ნაშთი კრედიტი')
    currency_id = fields.Many2one('res.currency', string='ვალუტა', help='Set only when all summed amount_currency use the same currency; otherwise empty.')
    currency_initial_debit = fields.Monetary(string='საწყისი ნაშთი დებიტი ვალუტაში', currency_field='currency_id')
    currency_initial_credit = fields.Monetary(string='საწყისი ნაშთი კრედიტი ვალუტაში', currency_field='currency_id')
    currency_brunva_debit = fields.Monetary(string='ბრუნვა დებიტი ვალუტაში', currency_field='currency_id')
    currency_brunva_credit = fields.Monetary(string='ბრუნვა კრედიტი ვალუტაში', currency_field='currency_id')
    currency_final_balance_debit = fields.Monetary(string='საბოლოო ნაშთი დებიტი ვალუტაში', currency_field='currency_id')
    currency_final_balance_credit = fields.Monetary(string='საბოლოო ნაშთი კრედიტი ვალუტაში', currency_field='currency_id')

    def action_view_entries(self):
        self.ensure_one()
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
        ]
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        else:
            domain.append(('partner_id', '=', False))
        if self.account_id:
            domain.append(('account_id', '=', self.account_id.id))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items - %s', self.partner or _('No Partner')),
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'search_default_group_by_move': 1},
        }
