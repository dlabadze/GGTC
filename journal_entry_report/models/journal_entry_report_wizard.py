from odoo import models, fields, api


class JournalEntryReportWizard(models.TransientModel):
    _name = 'journal.entry.report.wizard'
    _description = 'Journal Entry Excel Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    debit_accounts = fields.Many2many(
        'account.account',
        'journal_wizard_debit_account_rel',
        'wizard_id', 'account_id',
        string='Debit Account(s)',
        domain=[('deprecated', '=', False)],
        required=True
    )
    credit_accounts = fields.Many2many(
        'account.account',
        'journal_wizard_credit_account_rel',
        'wizard_id', 'account_id',
        string='Credit Account(s)',
        domain=[('deprecated', '=', False)],
        required=True
    )

    def action_generate_report(self):
        ir_default = self.env['ir.default'].sudo()

        ir_default.set(self._name, 'debit_accounts', self.debit_accounts.ids, user_id=self.env.uid)
        ir_default.set(self._name, 'credit_accounts', self.credit_accounts.ids, user_id=self.env.uid)

        start = self.start_date.strftime('%Y-%m-%d')
        end = self.end_date.strftime('%Y-%m-%d')
        debit_ids = ",".join(str(acc.id) for acc in self.debit_accounts)
        credit_ids = ",".join(str(acc.id) for acc in self.credit_accounts)
        is_nato_report = int(bool(self.env.context.get('is_nato_report')))

        return {
            'type': 'ir.actions.act_url',
            'url': (
                f"/journal_entry_excel/download?start_date={start}&end_date={end}"
                f"&debit_ids={debit_ids}&credit_ids={credit_ids}&nato={is_nato_report}"
            ),
            'target': 'self',
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        ir_default = self.env['ir.default'].sudo()

        debit_ids = ir_default._get(self._name, 'debit_accounts', user_id=self.env.uid)
        credit_ids = ir_default._get(self._name, 'credit_accounts', user_id=self.env.uid)

        if debit_ids:
            res['debit_accounts'] = [(6, 0, debit_ids)]
        if credit_ids:
            res['credit_accounts'] = [(6, 0, credit_ids)]

        return res