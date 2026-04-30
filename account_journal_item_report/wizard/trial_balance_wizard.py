from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
import base64
import xlsxwriter


class TrialBalanceWizard(models.TransientModel):
    _name = 'trial.balance.wizard'
    _description = 'Trial Balance Custom Wizard'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: self._get_default_start_date()
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=lambda self: self._get_default_end_date()
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    account_id = fields.Many2one('account.account', string='Account')
    partner_id = fields.Many2one('res.partner', string='Partner')

    def _get_default_start_date(self):
        last_start_date = self.env['ir.config_parameter'].sudo().get_param(
            f'trial_balance_last_start_date_{self.env.user.id}', False
        )
        if last_start_date:
            return fields.Date.from_string(last_start_date)
        else:
            return fields.Date.from_string(fields.Date.context_today(self)).replace(day=1)

    def _get_default_end_date(self):
        last_end_date = self.env['ir.config_parameter'].sudo().get_param(
            f'trial_balance_last_end_date_{self.env.user.id}', False
        )
        if last_end_date:
            return fields.Date.from_string(last_end_date)
        else:
            return fields.Date.context_today(self)

    def action_generate_report(self):
        self.ensure_one()
        if self.start_date > self.end_date:
            raise UserError(_('Start Date must be before End Date.'))

        self.env['trial.balance.result'].search([('wizard_id', '=', self.id)]).unlink()
        self.env['trial.balance.move.line'].search([('wizard_id', '=', self.id)]).unlink()

        accounts = self.env['account.account'].browse(self.account_id.id) if self.account_id else self.env['account.account'].search([])

        result_lines = []
        for account in accounts:
            base_domain = [('account_id', '=', account.id), ('parent_state', '=', 'posted')]
            partner_domain = [('partner_id', '=', self.partner_id.id)] if self.partner_id else []

            # opening lines (all lines before start_date)
            opening_lines = self.env['account.move.line'].search(
                base_domain + [('date', '<', self.start_date)] + partner_domain
            )
            # opening balance in company currency (GEL) - unchanged
            opening_balance_gel = sum(opening_lines.mapped('balance'))  # GEL

            period_lines = self.env['account.move.line'].search(
                base_domain + [('date', '>=', self.start_date), ('date', '<=', self.end_date)] + partner_domain,
                order='date asc, id asc'
            )

            currency = self.currency_id
            company_currency = self.env.company.currency_id

            # Find USD currency record (if exists) so we can exclude USD when reporting EUR
            currency_usd = self.env['res.currency'].search([('name', 'ilike', 'usd')], limit=1)

            def convert(amount):
                if company_currency != currency:
                    return company_currency._convert(amount, currency, self.env.company, self.end_date)
                return amount

            # Compute opening balance in selected currency:
            # - if company currency == report currency -> convert GEL opening to chosen currency
            # - else -> sum only opening_lines' amount_currency where currency matches report currency
            # Additionally exclude USD lines when reporting in EUR (requested change).
            if company_currency == currency:
                opening_balance_cur = round(convert(opening_balance_gel), 2)
            else:
                opening_balance_cur = 0.0
                for ol in opening_lines:
                    # include only lines that have amount_currency and currency matches report currency
                    # and (if report is EUR) exclude USD lines explicitly
                    if ol.amount_currency and ol.currency_id and ol.currency_id == currency:
                        # if report currency is EUR and an USD record was found, ensure we don't include USD (safety)
                        if currency.name and currency.name.strip().upper().startswith('EUR') and currency_usd and ol.currency_id == currency_usd:
                            # skip USD when reporting EUR
                            continue
                        opening_balance_cur += round(ol.amount_currency, 2)

            # Running balances initialised from opening balances
            running_balance = round(opening_balance_cur, 2)   # in selected currency
            running_balance_gel = round(opening_balance_gel, 2)        # in company currency

            # Period totals in selected currency (excluding GEL-only lines)
            period_debit_cur = 0.0
            period_credit_cur = 0.0

            move_line_vals = []

            for line in period_lines:
                partner = line.partner_id
                if not partner:
                    related_lines = line.move_id.line_ids
                    partners_in_move = related_lines.filtered(lambda l: l.partner_id)
                    if partners_in_move:
                        partner = partners_in_move[0].partner_id
                    elif line.move_id.partner_id:
                        partner = line.move_id.partner_id

                credit_in_currency = round(line.debit, 2) if line.debit > 0 else round(line.credit, 2)

                # Determine if this line is in the REPORT currency (foreign) or GEL-only
                # and exclude USD when reporting EUR (requested)
                is_report_currency = False
                if line.amount_currency and line.currency_id and line.currency_id == currency:
                    # if reporting in EUR and we have an USD currency record, ensure we don't accidentally include USD
                    if currency.name and currency.name.strip().upper().startswith('EUR') and currency_usd and line.currency_id == currency_usd:
                        is_report_currency = False
                    else:
                        is_report_currency = True

                debit = 0.0
                credit = 0.0
                if is_report_currency:
                    if line.amount_currency < 0:
                        credit = round(abs(line.amount_currency), 2)
                        period_credit_cur += credit
                    elif line.amount_currency > 0:
                        debit = round(line.amount_currency, 2)
                        period_debit_cur += debit

                    running_balance = round(running_balance + debit - credit, 2)
                else:
                    # GEL-only line: do NOT touch running_balance (currency view) and keep debit/credit 0.00
                    pass

                # GEL running balance always affected (both foreign and GEL lines) using company-currency amount
                if debit > 0:
                    running_balance_gel = round(running_balance_gel + credit_in_currency, 2)
                elif credit > 0:
                    running_balance_gel = round(running_balance_gel - credit_in_currency, 2)
                else:
                    # debit/credit are zero when GEL-only; adjust GEL running balance by signed balance
                    running_balance_gel = round(running_balance_gel + round(line.balance, 2), 2)

                currency_rate = 1.0
                if is_report_currency:
                    if credit > 0:
                        currency_rate = round(credit_in_currency / credit, 4) if credit else 1.0
                    elif debit > 0:
                        currency_rate = round(credit_in_currency / debit, 4) if debit else 1.0
                else:
                    currency_rate = 1.0

                move_line_vals.append((0, 0, {
                    'wizard_id': self.id,
                    'date': line.date,
                    'move_id': line.move_id.id,
                    'partner_id': partner.id if partner else False,
                    'name': line.name,
                    'debit': debit,
                    'credit': credit,
                    'running_balance': running_balance,
                    'ref': line.ref,
                    'currency_id': currency.id,
                    'comment': line.move_id.comment or '',
                    'currency_rate': currency_rate,
                    'credit_in_currency': credit_in_currency,   # GEL amount for display
                    'opening_balance_gel': running_balance_gel, # GEL running balance
                }))

            opening_balance_cur = round(opening_balance_cur, 2)
            closing_balance_cur = running_balance  # should equal opening + period movements in currency
            closing_balance_gel = running_balance_gel

            result_lines.append({
                'wizard_id': self.id,
                'account_id': account.id,
                'opening_balance': opening_balance_cur,                    # ვალუტაში (ONLY foreign lines if currency differs)
                'opening_balance_gel': round(opening_balance_gel, 2),      # ლარში (all lines)
                'period_debit': round(period_debit_cur, 2),                # მხოლოდ foreign currency ხაზები
                'period_credit': round(period_credit_cur, 2),              # მხოლოდ foreign currency ხაზები
                'closing_balance': round(closing_balance_cur, 2),          # ვალუტაში
                'closing_balance_gel': round(closing_balance_gel, 2),      # ლარში
                'currency_id': currency.id,
                'move_line_ids': move_line_vals,
            })

        self.env['trial.balance.result'].create(result_lines)

        self.env['ir.config_parameter'].sudo().set_param(
            f'trial_balance_last_start_date_{self.env.user.id}',
            fields.Date.to_string(self.start_date)
        )
        self.env['ir.config_parameter'].sudo().set_param(
            f'trial_balance_last_end_date_{self.env.user.id}',
            fields.Date.to_string(self.end_date)
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('მოძრაობის უწყისი'),
            'res_model': 'trial.balance.result',
            'view_mode': 'list,form',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': {
                'default_wizard_id': self.id,
                'group_by': ['account_id']
            },
            'views': [(False, 'list'), (False, 'form')],
        }


class TrialBalanceResult(models.TransientModel):
    _name = 'trial.balance.result'
    _description = 'მოძრაობის უწყისი'

    wizard_id = fields.Many2one('trial.balance.wizard', string='Wizard', ondelete='cascade')
    account_id = fields.Many2one('account.account', string='ანგარიში')
    opening_balance = fields.Monetary(string='საწყისი ნაშთი ვალუტაში')
    opening_balance_gel = fields.Monetary(string='საწყისი ნაშთი ლარში')
    period_debit = fields.Monetary(string='ბრუნვა დებეტი')
    period_credit = fields.Monetary(string='ბრუნვა კრედიტი')
    closing_balance = fields.Monetary(string='საბოლოო ნაშთი ვალუტაში')
    closing_balance_gel = fields.Monetary(string='საბოლოო ნაშთი ლარში')
    currency_id = fields.Many2one('res.currency', string='ვალუტა')
    move_line_ids = fields.One2many('trial.balance.move.line', 'result_id', string='Journal Items')

    def action_export_excel(self):
        self.ensure_one()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(f"Account {self.account_id.code or 'Report'}")

        # Define formats
        bold = workbook.add_format({'bold': True, 'font_size': 12})
        header = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        money = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text = workbook.add_format({'border': 1})

        # Write report header
        sheet.write('A1', 'მოძრაობის უწყისი', bold)
        sheet.write('A2', f'ანგარიში: {self.account_id.code} - {self.account_id.name}', bold)
        sheet.write('A3', f'ვალუტა: {self.currency_id.name}', bold)

        # Account summary
        sheet.write('A5', 'საწყისი ნაშთი ვალუტაში:', header)
        sheet.write('B5', self.opening_balance, money)
        sheet.write('A6', 'საწყისი ნაშთი ლარში:', header)
        sheet.write('B6', self.opening_balance_gel, money)
        sheet.write('A7', 'ბრუნვა დებეტი:', header)
        sheet.write('B7', self.period_debit, money)
        sheet.write('A8', 'ბრუნვა კრედიტი:', header)
        sheet.write('B8', self.period_credit, money)
        sheet.write('A9', 'საბოლოო ნაშთი ვალუტაში:', header)
        sheet.write('B9', self.closing_balance, money)
        sheet.write('A10', 'საბოლოო ნაშთი ლარში:', header)
        sheet.write('B10', self.closing_balance_gel, money)

        # Move lines header
        sheet.write('A12', 'თარიღი', header)
        sheet.write('B12', 'ჟურნალის ჩანაწერი', header)
        sheet.write('C12', 'პარტნიორი', header)
        sheet.write('D12', 'კომენტარი', header)
        sheet.write('E12', 'ბრუნვა დებეტი ვალუტაში', header)
        sheet.write('F12', 'ბრუნვა კრედიტი ვალუტაში', header)
        sheet.write('G12', 'ნაშთი ვალუტაში', header)
        sheet.write('H12', 'ბრუნვა ლარში', header)
        sheet.write('I12', 'ნაშთი ლარში', header)
        sheet.write('J12', 'ვალუტის კურსი', header)
        sheet.write('K12', 'Reference', header)

        # Write move lines data
        row = 13
        for line in self.move_line_ids:
            sheet.write(row, 0, str(line.date), text)
            sheet.write(row, 1, line.move_id.name or '', text)
            sheet.write(row, 2, line.partner_id.name if line.partner_id else '', text)
            sheet.write(row, 3, line.comment or '', text)
            sheet.write(row, 4, line.debit, money)
            sheet.write(row, 5, line.credit, money)
            sheet.write(row, 6, line.running_balance, money)
            sheet.write(row, 7, line.credit_in_currency, money)
            sheet.write(row, 8, line.opening_balance_gel, money)
            sheet.write(row, 9, line.currency_rate, money)
            sheet.write(row, 10, line.ref or '', text)
            row += 1

        # Auto-adjust column widths
        sheet.set_column('A:A', 12)  # Date
        sheet.set_column('B:B', 20)  # Move
        sheet.set_column('C:C', 20)  # Partner
        sheet.set_column('D:D', 30)  # Comment
        sheet.set_column('E:K', 15)  # Money columns

        workbook.close()
        output.seek(0)

        filename = f"trial_balance_{self.account_id.code or 'account'}_{fields.Date.today().strftime('%Y%m%d')}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class TrialBalanceMoveLine(models.TransientModel):
    _name = 'trial.balance.move.line'
    _description = 'Trial Balance Move Line'

    wizard_id = fields.Many2one('trial.balance.wizard', string='Wizard', ondelete='cascade')
    result_id = fields.Many2one('trial.balance.result', string='Result', ondelete='cascade')
    date = fields.Date(string='თარიღი')
    move_id = fields.Many2one('account.move', string='ჟურნალის ჩანაწერი')
    partner_id = fields.Many2one('res.partner', string='პარტნიორი')
    name = fields.Char(string='Label')
    debit = fields.Monetary(string='ბრუნვა დებეტი ვალუტაში')
    credit = fields.Monetary(string='ბრუნვა კრედიტი ვალუტაში')
    running_balance = fields.Monetary(string='ნაშთი ვალუტაში')
    ref = fields.Char(string='Reference')
    currency_id = fields.Many2one('res.currency', string='Currency')
    comment = fields.Text(string='კომენტარი')
    currency_rate = fields.Float(string='ვალუტის კურსი', digits=(12, 4))
    credit_in_currency = fields.Monetary(string='ბრუნვა ლარში')
    opening_balance_gel = fields.Monetary(string='ნაშთი ლარში')



