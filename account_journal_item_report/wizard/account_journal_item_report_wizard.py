from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountJournalItemReportWizard(models.TransientModel):
    _name = 'account.journal.item.report.wizard'
    _description = 'Journal Item Report Wizard'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    starting_balance = fields.Monetary(string='Starting Balance', compute='_compute_balances', store=False)
    ending_balance = fields.Monetary(string='Ending Balance', compute='_compute_balances', store=False)
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency', store=False)

    @api.depends('account_id', 'start_date', 'end_date')
    def _compute_balances(self):
        for wizard in self:
            if wizard.account_id and wizard.start_date and wizard.end_date:
                wizard.starting_balance = wizard._get_balance(wizard.account_id.id, wizard.start_date, before=True)
                wizard.ending_balance = wizard._get_balance(wizard.account_id.id, wizard.end_date, before=False)
            else:
                wizard.starting_balance = 0.0
                wizard.ending_balance = 0.0

    @api.depends('account_id')
    def _compute_currency(self):
        for wizard in self:
            wizard.currency_id = wizard.account_id.currency_id or self.env.company.currency_id

    def action_generate_report(self):
        self.ensure_one()
        if self.start_date > self.end_date:
            raise UserError(_('Start Date must be before End Date.'))

        # Remove previous results for this user/session
        self.env['account.journal.item.report.result'].search([('wizard_id', '=', self.id)]).unlink()

        # Compute opening and closing balances
        opening_balance = self._get_balance(self.account_id.id, self.start_date, before=True)
        closing_balance = self._get_balance(self.account_id.id, self.end_date, before=False)
        # Get move lines in range
        domain = [
            ('account_id', '=', self.account_id.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', self.start_date),
            ('date', '<=', self.end_date),
        ]
        move_lines = self.env['account.move.line'].search(domain, order='date asc, id asc')

        result_lines = []

        for line in move_lines:
            result_lines.append({
                'wizard_id': self.id,
                'date': line.date,
                'journal_id': line.journal_id.id,
                'move_id': line.move_id.id,
                'partner_id': line.partner_id.id if line.partner_id else False,
                'name': line.name,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.balance,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
                'ref': line.ref,
                'currency_id': line.currency_id.id or self.currency_id.id,
                'account_id': line.account_id.id,
            })

        self.env['account.journal.item.report.result'].create(result_lines)

        # Compose the help message
        help_message = _(
            "<b>Opening Balance:</b> %s<br/><b>Closing Balance:</b> %s"
        ) % (opening_balance, closing_balance)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Item Report'),
            'res_model': 'account.journal.item.report.result',
            'view_mode': 'list,form',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': {'default_wizard_id': self.id, 'group_by': ['account_id']},
            'views': [(False, 'list'), (False, 'form')],
            'help': help_message,
        }

    def _get_balance(self, account_id, date, before=True):
        domain = [('account_id', '=', account_id), ('parent_state', '=', 'posted')]
        if before:
            domain.append(('date', '<', date))
        else:
            domain.append(('date', '<=', date))
        lines = self.env['account.move.line'].search(domain)
        balance = sum(lines.mapped('balance'))
        return balance

class AccountJournalItemReportResult(models.TransientModel):
    _name = 'account.journal.item.report.result'
    _description = 'Journal Item Report Result'

    wizard_id = fields.Many2one('account.journal.item.report.wizard', string='Wizard', ondelete='cascade')
    date = fields.Date(string='Date')
    journal_id = fields.Many2one('account.journal', string='Journal')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    partner_id = fields.Many2one('res.partner', string='Partner')
    name = fields.Char(string='Label')
    debit = fields.Monetary(string='Debit')
    credit = fields.Monetary(string='Credit')
    balance = fields.Monetary(string='Balance')
    opening_balance = fields.Monetary(string='Opening Balance')
    closing_balance = fields.Monetary(string='Closing Balance')
    ref = fields.Char(string='Reference')
    currency_id = fields.Many2one('res.currency', string='Currency')
    account_id = fields.Many2one('account.account', string='Account') 