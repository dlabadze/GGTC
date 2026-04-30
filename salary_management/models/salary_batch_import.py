from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SalaryBatchImport(models.Model):
    _name = 'salary.batch.import'
    _description = 'Salary Batch Import'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    amount = fields.Float(string='Amount', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    debit_account_id = fields.Many2one('account.account', string='Debit Account', required=True)
    credit_account_id = fields.Many2one('account.account', string='Credit Account', required=True)
    reference = fields.Char(string='Reference')
    is_income_tax = fields.Boolean(string='საშემოსავლო')
    is_pension = fields.Boolean(string='საპენსიო')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted')
    ], string='Status', default='draft', copy=False)
    journal_entry_id = fields.Many2one('account.move', string='Journal Entry')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('salary.import') or _('New')
        return super().create(vals_list)

    def action_post_entry(self):
        self.ensure_one()
        if self.state == 'posted':
            raise UserError(_("Entry has already been posted."))

        move_lines = []
        # Main entry
        move_lines.extend([
            (0, 0, {
                'account_id': self.debit_account_id.id,
                'partner_id': self.partner_id.id,
                'debit': self.amount,
                'credit': 0,
                'name': self.reference or f"Salary for {self.partner_id.name}"
            }),
            (0, 0, {
                'account_id': self.credit_account_id.id,
                'partner_id': self.partner_id.id,
                'debit': 0,
                'credit': self.amount,
                'name': self.reference or f"Salary for {self.partner_id.name}"
            })
        ])

        # Create journal entry
        move = self.env['account.move'].create({
            'ref': self.reference or f"Salary for {self.partner_id.name}",
            'date': self.date,
            'journal_id': self.journal_id.id,
            'line_ids': move_lines
        })

        self.write({
            'journal_entry_id': move.id,
            'state': 'posted'
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Journal entry has been generated.'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.journal_entry_id.id,
        }