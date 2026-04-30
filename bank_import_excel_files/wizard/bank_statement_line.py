from odoo import models, api


class BankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.model
    def _prepare_move_line_default_vals(self, counterpart_account_id=None):
        vals_list = super()._prepare_move_line_default_vals(counterpart_account_id)

        ALLOWED_JOURNALS = [
            'GE90LB0113172770216000',
            'თიბისი ფეი',
            'GE17TB7722636020100004',
            'GE81BG0000000499211307',
            'GE40BG0000000499210105',
            'GE22TB7722636020100011',
            'GE56TB7722645067800007',
            'GE09LB0113150423521000',
            'GE21LB0113122202198000',
            'GE73BG0000000176620200',
        ]

        if self.journal_id.name not in ALLOWED_JOURNALS:
            return vals_list

        income_account = self.env['account.account'].search([('code', '=', '1242')], limit=1)

        if not income_account:
            return vals_list

        if self.journal_id.name in ALLOWED_JOURNALS and self.amount > 0:
            income_account = self.env['account.account'].search([('code', '=', '1242')], limit=1)
            if income_account:
                for line_vals in vals_list:
                    if line_vals['account_id'] != self.journal_id.default_account_id.id:
                        line_vals['account_id'] = income_account.id
        return vals_list