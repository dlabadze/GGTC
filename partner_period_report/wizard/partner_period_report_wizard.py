from odoo import models, fields, _
from odoo.exceptions import UserError


class PartnerPeriodReportWizard(models.TransientModel):
    _name = 'partner.period.report.wizard'
    _description = 'Partner Period Report Wizard'

    account_id = fields.Many2one('account.account', string='Account', required=True)
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    def action_generate_report(self):
        cr = self._cr
        account_id = self.account_id.id
        date_from = self.date_from
        date_to = self.date_to

        cr.execute("""
            SELECT aml.partner_id,
                   COALESCE(SUM(aml.debit), 0)  AS initial_debit,
                   COALESCE(SUM(aml.credit), 0) AS initial_credit,
                   COALESCE(SUM(aml.amount_currency) FILTER (WHERE aml.currency_id IS NOT NULL), 0) AS initial_amount_currency,
                   COUNT(DISTINCT aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS initial_currency_count,
                   MIN(aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS initial_currency_id
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.account_id = %(account_id)s
              AND am.state = 'posted'
              AND am.date < %(date_from)s
              AND aml.partner_id IS NOT NULL
            GROUP BY aml.partner_id
        """, {'account_id': account_id, 'date_from': date_from})
        initial_data = cr.fetchall()
        initial_rows = {
            row[0]: {
                'initial_debit': row[1],
                'initial_credit': row[2],
                'initial_amount_currency': float(row[3] or 0),
                'initial_currency_count': row[4] or 0,
                'initial_currency_id': row[5],
            }
            for row in initial_data
        }

        cr.execute("""
            SELECT COALESCE(SUM(aml.debit), 0)  AS initial_debit,
                   COALESCE(SUM(aml.credit), 0) AS initial_credit,
                   COALESCE(SUM(aml.amount_currency) FILTER (WHERE aml.currency_id IS NOT NULL), 0) AS initial_amount_currency,
                   COUNT(DISTINCT aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS initial_currency_count,
                   MIN(aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS initial_currency_id
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.account_id = %(account_id)s
              AND am.state = 'posted'
              AND am.date < %(date_from)s
              AND aml.partner_id IS NULL
        """, {'account_id': account_id, 'date_from': date_from})
        initial_null_data = cr.fetchone()
        if initial_null_data and any(initial_null_data):
            initial_rows[False] = {
                'initial_debit': initial_null_data[0],
                'initial_credit': initial_null_data[1],
                'initial_amount_currency': float(initial_null_data[2] or 0),
                'initial_currency_count': initial_null_data[3] or 0,
                'initial_currency_id': initial_null_data[4],
            }

        cr.execute("""
            SELECT aml.partner_id,
                   COALESCE(SUM(aml.debit), 0)  AS brunva_debit,
                   COALESCE(SUM(aml.credit), 0) AS brunva_credit,
                   COALESCE(SUM(aml.amount_currency) FILTER (WHERE aml.currency_id IS NOT NULL), 0) AS brunva_amount_currency,
                   COUNT(DISTINCT aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS brunva_currency_count,
                   MIN(aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS brunva_currency_id
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.account_id = %(account_id)s
              AND am.state = 'posted'
              AND am.date >= %(date_from)s
              AND am.date <= %(date_to)s
              AND aml.partner_id IS NOT NULL
            GROUP BY aml.partner_id
        """, {'account_id': account_id, 'date_from': date_from, 'date_to': date_to})
        turnover_data = cr.fetchall()
        turnover_rows = {
            row[0]: {
                'brunva_debit': row[1],
                'brunva_credit': row[2],
                'brunva_amount_currency': float(row[3] or 0),
                'brunva_currency_count': row[4] or 0,
                'brunva_currency_id': row[5],
            }
            for row in turnover_data
        }

        cr.execute("""
            SELECT COALESCE(SUM(aml.debit), 0)  AS brunva_debit,
                   COALESCE(SUM(aml.credit), 0) AS brunva_credit,
                   COALESCE(SUM(aml.amount_currency) FILTER (WHERE aml.currency_id IS NOT NULL), 0) AS brunva_amount_currency,
                   COUNT(DISTINCT aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS brunva_currency_count,
                   MIN(aml.currency_id) FILTER (WHERE aml.currency_id IS NOT NULL) AS brunva_currency_id
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            WHERE aml.account_id = %(account_id)s
              AND am.state = 'posted'
              AND am.date >= %(date_from)s
              AND am.date <= %(date_to)s
              AND aml.partner_id IS NULL
        """, {'account_id': account_id, 'date_from': date_from, 'date_to': date_to})
        turnover_null_data = cr.fetchone()
        if turnover_null_data and any(turnover_null_data):
            turnover_rows[False] = {
                'brunva_debit': turnover_null_data[0],
                'brunva_credit': turnover_null_data[1],
                'brunva_amount_currency': float(turnover_null_data[2] or 0),
                'brunva_currency_count': turnover_null_data[3] or 0,
                'brunva_currency_id': turnover_null_data[4],
            }

        all_partner_ids = set(initial_rows) | set(turnover_rows)
        if not all_partner_ids:
            raise UserError(_('No data found for the selected period and account.'))

        gel_currency = self.env['res.currency'].search([('name', '=', 'GEL')], limit=1)
        partners = self.env['res.partner'].browse([pid for pid in all_partner_ids if pid])
        vals_list = []
        for pid in all_partner_ids:
            init = initial_rows.get(pid, {
                'initial_debit': 0.0, 'initial_credit': 0.0,
                'initial_amount_currency': 0.0, 'initial_currency_count': 0, 'initial_currency_id': None,
            })
            turn = turnover_rows.get(pid, {
                'brunva_debit': 0.0, 'brunva_credit': 0.0,
                'brunva_amount_currency': 0.0, 'brunva_currency_count': 0, 'brunva_currency_id': None,
            })

            debits = init['initial_debit']
            credits = init['initial_credit']
            if debits > credits:
                initial_balance_debit = debits - credits
                initial_balance_credit = 0.0
            elif credits > debits:
                initial_balance_debit = 0.0
                initial_balance_credit = credits - debits
            else:
                initial_balance_debit = 0.0
                initial_balance_credit = 0.0

            total_debit = debits + turn['brunva_debit']
            total_credit = credits + turn['brunva_credit']
            final_debit = max(total_debit - total_credit, 0.0)
            final_credit = max(total_credit - total_debit, 0.0)

            # Currency columns come ONLY from account.move.line amount_currency sum. Never from debit/credit.
            # When amount_currency is 0 or empty in every record, all currency_* fields are 0.
            initial_curr = float(init.get('initial_amount_currency') or 0)
            brunva_curr = float(turn.get('brunva_amount_currency') or 0)
            if initial_curr > 0:
                currency_initial_debit = initial_curr
                currency_initial_credit = 0.0
            elif initial_curr < 0:
                currency_initial_debit = 0.0
                currency_initial_credit = abs(initial_curr)
            else:
                currency_initial_debit = 0.0
                currency_initial_credit = 0.0

            if brunva_curr > 0:
                currency_brunva_debit = brunva_curr
                currency_brunva_credit = 0.0
            elif brunva_curr < 0:
                currency_brunva_debit = 0.0
                currency_brunva_credit = abs(brunva_curr)
            else:
                currency_brunva_debit = 0.0
                currency_brunva_credit = 0.0

            final_curr = initial_curr + brunva_curr
            if final_curr > 0:
                currency_final_balance_debit = final_curr
                currency_final_balance_credit = 0.0
            elif final_curr < 0:
                currency_final_balance_debit = 0.0
                currency_final_balance_credit = abs(final_curr)
            else:
                currency_final_balance_debit = 0.0
                currency_final_balance_credit = 0.0

            # Set currency_id only when all summed amount_currency use the same currency and at least one sum is non-zero; otherwise keep empty.
            # If every record has amount_currency = 0, keep currency_id empty and amounts are already 0.
            # If currency is GEL, do not set currency_id and keep all currency_* fields 0.
            init_cc = init.get('initial_currency_count') or 0
            turn_cc = turn.get('brunva_currency_count') or 0
            init_cid = init.get('initial_currency_id')
            turn_cid = turn.get('brunva_currency_id')
            report_currency_id = False
            if (initial_curr != 0 or brunva_curr != 0) and init_cc <= 1 and turn_cc <= 1:
                if init_cc == 1 and turn_cc == 1 and init_cid and turn_cid and init_cid == turn_cid:
                    report_currency_id = init_cid
                elif init_cc == 1 and turn_cc == 0 and init_cid:
                    report_currency_id = init_cid
                elif init_cc == 0 and turn_cc == 1 and turn_cid:
                    report_currency_id = turn_cid
            if report_currency_id and gel_currency and report_currency_id == gel_currency.id:
                report_currency_id = False
                currency_initial_debit = 0.0
                currency_initial_credit = 0.0
                currency_brunva_debit = 0.0
                currency_brunva_credit = 0.0
                currency_final_balance_debit = 0.0
                currency_final_balance_credit = 0.0

            vals_list.append({
                'date_from': date_from,
                'date_to': date_to,
                'account_id': account_id,
                'partner_id': pid,
                'partner': partners.browse(pid).name if pid else 'None',
                'initial_balance_debit': initial_balance_debit,
                'initial_balance_credit': initial_balance_credit,
                'brunva_debit': turn['brunva_debit'],
                'brunva_credit': turn['brunva_credit'],
                'final_balance_debit': final_debit,
                'final_balance_credit': final_credit,
                'currency_id': report_currency_id,
                'currency_initial_debit': currency_initial_debit,
                'currency_initial_credit': currency_initial_credit,
                'currency_brunva_debit': currency_brunva_debit,
                'currency_brunva_credit': currency_brunva_credit,
                'currency_final_balance_debit': currency_final_balance_debit,
                'currency_final_balance_credit': currency_final_balance_credit,
            })

        created = self.env['partner.period.report'].sudo().create(vals_list)

        account = self.env['account.account'].browse(account_id)
        return {
            'type': 'ir.actions.act_window',
            'name': f'{date_from} - {date_to} ანგარიში ({account.code})',
            'res_model': 'partner.period.report',
            'view_mode': 'list',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }
            




