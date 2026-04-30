from odoo import models, fields, api


class JournalEntryReportWizard(models.TransientModel):
    _name = 'journal.entry.report.wizard.2'
    _description = 'Journal Entry Excel Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    debit_accounts = fields.Many2many(
        'account.account',
        'journal_wizard_debit_account_rel_2',
        'wizard_id',
        'account_id',
        string='Debit Account(s)',
        domain=[('deprecated', '=', False)],
        required=True
    )
    credit_accounts = fields.Many2many(
        'account.account',
        'journal_wizard_credit_account_rel_2',
        'wizard_id',
        'account_id',
        string='Credit Account(s)',
        domain=[('deprecated', '=', False)],
        required=True
    )

    def action_generate_report(self):
        self.env['ir.default'].set(self._name, 'debit_accounts', self.debit_accounts.ids)
        self.env['ir.default'].set(self._name, 'credit_accounts', self.credit_accounts.ids)

        start = self.start_date.strftime('%Y-%m-%d')
        end = self.end_date.strftime('%Y-%m-%d')
        debit_ids = ",".join(str(acc.id) for acc in self.debit_accounts)
        credit_ids = ",".join(str(acc.id) for acc in self.credit_accounts)
        download_url = (
            f"/journal_entry_excel_2/download?start_date={start}&end_date={end}"
            f"&debit_ids={debit_ids}&credit_ids={credit_ids}"
        )
        return {'type': 'ir.actions.act_url', 'url': download_url, 'target': 'self'}

    @api.model
    def default_get(self, field_names):
        res = super().default_get(field_names)
        ir_default = self.env['ir.default']
        debit_ids = ir_default._get(self._name, 'debit_accounts')
        credit_ids = ir_default._get(self._name, 'credit_accounts')
        if debit_ids:
            res['debit_accounts'] = [(6, 0, debit_ids)]
        if credit_ids:
            res['credit_accounts'] = [(6, 0, credit_ids)]
        return res

