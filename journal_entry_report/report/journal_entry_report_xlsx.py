from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime
from collections import defaultdict

SHEGAVATI_DEFAULT_LIMIT = 0.0
TAX_ACCOUNT_CODE = '3370'
PENSION_ACCOUNT_CODE = '3320'
import logging
_logger = logging.getLogger(__name__)

REPORT_HEADERS = [
    'საიდენტიფიკაციო ნომერი',
    'მიმღების სახელი',
    'მიმღების გვარი',
    'მისამართი',
    'რეზიდენტობა',
    'კატეგორია',
    'განაცემის სახე',
    'განაცემი თანხა',
    'სხვა შეღავათები',
    'for testing',
    'საპენსიო',
    'საშემოსავლო',
    'გაცემის თარიღი',
    'განაკვეთი',
    'გათავისუფლებული',
    'ჩათვლას დაქვემდებარებული',
]
NATO_EXCLUDED_HEADERS = {'for testing', 'საპენსიო', 'საშემოსავლო'}


def get_report_headers(is_nato_report=False):
    if not is_nato_report:
        return REPORT_HEADERS
    return [header for header in REPORT_HEADERS if header not in NATO_EXCLUDED_HEADERS]


def compute_adjusted_amount(debit, is_special, shegavati_used, shegavati_limit, partner_id=None):

    special_divisor = 0.784
    regular_divisor = 0.8
    special_divisor_within = 0.98
    regular_divisor_within = 1.0

    gross_divisor = special_divisor if is_special else regular_divisor
    exempt_divisor = special_divisor_within if is_special else regular_divisor_within

    remaining_exemption = shegavati_limit - shegavati_used

    if remaining_exemption <= 0:
        adjusted = round(debit / gross_divisor, 2)
        if partner_id.id == 5330:
            _logger.info(f"გოჩა ბუჩუკური: პირველი შემთხვევა: adjusted: {adjusted}, remaining_exemption: {remaining_exemption}, shegavati_limit: {shegavati_limit}, shegavati_used: {shegavati_used}")
        if partner_id.id == 7258:
            _logger.info(f"გიორგი ბედოიძე: პირველი შემთხვევა: adjusted: {adjusted}, remaining_exemption: {remaining_exemption}, shegavati_limit: {shegavati_limit}, shegavati_used: {shegavati_used}")
        return adjusted, shegavati_used, 0.0

    if debit <= remaining_exemption:
        adjusted = round(debit / exempt_divisor, 2)
        if partner_id.id == 5330:
            _logger.info(f"გოჩა ბუჩუკური: მეორე შემთხვევა: adjusted: {adjusted}, remaining_exemption: {remaining_exemption}, shegavati_limit: {shegavati_limit}, shegavati_used: {shegavati_used}")
        if partner_id.id == 7258:
            _logger.info(f"გიორგი ბედოიძე: მეორე შემთხვევა: adjusted: {adjusted}, remaining_exemption: {remaining_exemption}, shegavati_limit: {shegavati_limit}, shegavati_used: {shegavati_used}")
        return adjusted, shegavati_used + debit, debit

    exempt_part = remaining_exemption
    taxable_part = debit - remaining_exemption

    adjusted_exempt = round(exempt_part / exempt_divisor, 2)
    adjusted_taxable = round(taxable_part / gross_divisor, 2)
    total_adjusted = adjusted_exempt + adjusted_taxable
    if partner_id.id == 5330:
        _logger.info(f"გოჩა ბუჩუკური: მესამე შემთხვევა: total_adjusted: {total_adjusted}, remaining_exemption: {remaining_exemption}, shegavati_limit: {shegavati_limit}, shegavati_used: {shegavati_used}")
    if partner_id.id == 7258:
        _logger.info(f"გიორგი ბედოიძე: მესამე შემთხვევა: total_adjusted: {total_adjusted}, remaining_exemption: {remaining_exemption}, shegavati_limit: {shegavati_limit}, shegavati_used: {shegavati_used}")

    return total_adjusted, shegavati_used + exempt_part, exempt_part


def get_initial_shegavati_usage(su_env, partner, contact_start_date, report_start_date,
                                debit_codes, credit_codes, shegavati_limit):

    """შეღავათის უკვე გამოყენებული თანხა: დებეტი/კრედიტის დაწყვილება, როგორც journal_entry_report_2-ში."""
    if not contact_start_date:
        return 0.0
    if shegavati_limit <= 0:
        return 0.0
    if partner.id == 5330:
        _logger.info(f"გოჩა ბუჩუკური: contact_start_date: {contact_start_date}, report_start_date: {report_start_date}, shegavati_limit: {shegavati_limit}")
        _logger.info(f"გოჩა ბუჩუკური: debit_codes: {debit_codes}, credit_codes: {credit_codes}")
    historical_lines = su_env['account.move.line'].sudo().search([
        ('date', '>=', contact_start_date),
        ('date', '<', report_start_date),
        ('partner_id', '=', partner.id),
        ('account_id.code', 'in', debit_codes + credit_codes),
        ('move_id.state', '=', 'posted'),
    ], order='date asc')

    credit_3370 = su_env['account.move.line'].sudo().search([
        ('date', '>=', contact_start_date),
        ('date', '<', report_start_date),
        ('partner_id', '=', partner.id),
        ('account_id.code', '=', '3370'),
        ('move_id.state', '=', 'posted'),
        ('name', 'ilike', 'საპენსიო'),
    ], order='date asc')

    debit_lines = [l for l in historical_lines if l.debit > 0 and l.account_id.code in debit_codes]
    total_historical_debit = sum(l.debit for l in debit_lines)
    total_credit_3370 = sum(line.credit for line in credit_3370)

   
    # Historical debit already consumed the full benefit threshold.
    diff = total_historical_debit - total_credit_3370
    if partner.id == 5330:
        _logger.info(f"-|"*100)
        _logger.info(f"გოჩა ბუჩუკური: credit_3370: {credit_3370}")
        _logger.info(f"გოჩა ბუჩუკური: total_historical_debit: {total_historical_debit}, total_credit_3370: {total_credit_3370}")
        _logger.info(f"გოჩა ბუჩუკური: shegavati_limit: {shegavati_limit}")
        _logger.info(f"გოჩა ბუჩუკური: diff: {diff}")
    if diff >= shegavati_limit:
        return shegavati_limit
    return diff
# Partner display helpers

def split_full_name(full_name):
    parts = (full_name or '').strip().split()
    first = parts[0] if parts else ''
    surname = ' '.join(parts[1:]) if len(parts) > 1 else ''
    return first, surname


def get_partner_address_and_country(partner):
    employee = partner.employee_ids[:1]
    if employee:
        address = f"{employee.private_street or ''}"
        country_name = (employee.private_country_id.name or '').strip()
    else:
        address = f"{partner.street or ''}"
        country_name = (partner.country_id.name or '').strip()
    return address, country_name


# Excel workbook helpers

def build_workbook_worksheet(output, headers):
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Journal Entries')

    header_fmt = workbook.add_format({
        'bold': True,
        'border': 1,
        'align': 'center',
        'text_wrap': True,
    })
    worksheet.set_column(0, max(len(headers) - 1, 0), 25)

    for col, title in enumerate(headers):
        worksheet.write(0, col, title, header_fmt)

    return workbook, worksheet


# Data fetching helpers

def fetch_account_codes(su_env, ids_str):
    if not ids_str:
        return []
    ids = [int(i) for i in ids_str.split(',')]
    return su_env['account.account'].browse(ids).mapped('code')


def fetch_matched_debit_lines(su_env, start_date, end_date, debit_codes, credit_codes):
    all_debits = su_env['account.move.line'].sudo().search([
        ('date', '>=', start_date),
        ('date', '<=', end_date),
        ('debit', '>', 0),
        ('partner_id', '!=', False),
        ('account_id.code', 'in', debit_codes),
        ('move_id.state', '=', 'posted'),
    ], order='date asc')

    matched = []
    used_debit_ids = set()
    used_credit_ids = set()

    for move in all_debits.mapped('move_id'):
        move_debits = [
            l for l in move.line_ids
            if start_date <= l.date <= end_date
            and l.account_id.code in debit_codes
            and l.debit > 0
        ]
        move_credits = [
            l for l in move.line_ids
            if start_date <= l.date <= end_date
            and l.account_id.code in credit_codes
            and l.credit > 0
        ]

        for d in move_debits:
            if d.id in used_debit_ids:
                continue
            for c in move_credits:
                if c.id in used_credit_ids:
                    continue
                if abs(d.debit - c.credit) <= 0.01:
                    matched.append(d)
                    used_debit_ids.add(d.id)
                    used_credit_ids.add(c.id)
                    break

    return matched


# def fetch_tax_and_pension_amounts(su_env, grouped_data, line_references, start_date, end_date):

#     relevant_move_ids = [line_references[key].move_id.id for key in grouped_data]

#     tax_pension_lines = su_env['account.move.line'].sudo().search([
#         ('move_id', 'in', relevant_move_ids),
#         ('credit', '>', 0),
#         ('account_id.code', 'in', [TAX_ACCOUNT_CODE, PENSION_ACCOUNT_CODE]),
#         ('move_id.state', '=', 'posted'),
#     ])

#     amounts_tax = defaultdict(float)     # account 3370
#     amounts_pension = defaultdict(float)  # account 3320

#     for tpl in tax_pension_lines:
#         for key, ref_line in line_references.items():
#             if ref_line.move_id.id != tpl.move_id.id:
#                 continue
#             if tpl.account_id.code == TAX_ACCOUNT_CODE:
#                 amounts_tax[key] += tpl.credit
#             elif tpl.account_id.code == PENSION_ACCOUNT_CODE:
#                 amounts_pension[key] += tpl.credit

#     return amounts_tax, amounts_pension

def fetch_tax_and_pension_amounts(adjusted_amount, is_special, exempt_debit_this_line):
    """Pension 2% on adjusted when special. Tax 20% on amount after pension and this line's shegavati debit."""
    amount_pension = round(adjusted_amount * 0.02, 2) if is_special else 0.0
    amount_tax = round(
        (adjusted_amount - amount_pension - exempt_debit_this_line) * 0.2,
        2,
    )
    return amount_tax, amount_pension

class JournalEntryExcelReport(http.Controller):

    @http.route('/journal_entry_excel/download', type='http', auth='user')
    def download_excel_report(self, start_date, end_date, debit_ids, credit_ids, nato=0):
        su_env = request.env['res.users'].sudo().env
        is_nato_report = str(nato).lower() in ('1', 'true', 'yes')

        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        debit_codes = fetch_account_codes(su_env, debit_ids)
        credit_codes = fetch_account_codes(su_env, credit_ids)

        #Collect and group matched debit lines by (partner, date)
        matched_debit_lines = fetch_matched_debit_lines(
            su_env, start_date_dt, end_date_dt, debit_codes, credit_codes
        )

        grouped_totals = defaultdict(float)
        line_references = {}

        for line in matched_debit_lines:
            key = (line.partner_id.id, line.date)
            grouped_totals[key] += line.debit
            if key not in line_references:
                line_references[key] = line

        #Pre-fetch tax & pension amounts per move
        # amounts_tax, amounts_pension = fetch_tax_and_pension_amounts(
        #     su_env, grouped_totals, line_references, start_date_dt, end_date_dt
        # )
        #Country code lookup map
        country_code_map = {
            rec.country_name.strip(): rec.country_code
            for rec in su_env['res.country.code.map'].search([])
        }
        headers = get_report_headers(is_nato_report)
        output = io.BytesIO()
        workbook, worksheet = build_workbook_worksheet(output, headers)

        partner_shegavati_usage = defaultdict(float)
        row = 1

        for key in sorted(grouped_totals.keys(), key=lambda k: k[1]):
            _, line_date = key
            total_debit = grouped_totals[key]
            ref_line = line_references[key]
            partner = ref_line.partner_id.sudo()

            shegavati_start_date = partner.x_studio_start_date_1
            shegavati_limit = partner.x_studio_shegavati or SHEGAVATI_DEFAULT_LIMIT
            if partner.id == 5330:
                _logger.info(f"გოჩა ბუჩუკური: shegavati_start_date: {shegavati_start_date}, shegavati_limit: {shegavati_limit}")
            if partner.id not in partner_shegavati_usage:
                partner_shegavati_usage[partner.id] = get_initial_shegavati_usage(
                    su_env,
                    partner,
                    shegavati_start_date,
                    start_date_dt,
                    debit_codes,
                    credit_codes,
                    shegavati_limit,
                )

            # Apply shegavati only from its configured start date.
            # If start date is missing or this line is before start date, no shegavati is applied.
            effective_shegavati_limit = (
                shegavati_limit
                if shegavati_start_date and line_date >= shegavati_start_date
                else 0.0
            )

            is_special = bool(
                getattr(partner, 'x_studio_checkbox', False)
                or getattr(partner, 'x_studio_', False)
            )
            shegavati_used = partner_shegavati_usage[partner.id]
            if partner.id == 5330:
                _logger.info(f"გოჩა ბუჩუკური: total_debit: {total_debit}, is_special: {is_special}, shegavati_used: {shegavati_used}, effective_shegavati_limit: {effective_shegavati_limit}")
            if partner.id == 7258:
                _logger.info(f"გიორგი ბედოიძე: total_debit: {total_debit}, is_special: {is_special}, shegavati_used: {shegavati_used}, effective_shegavati_limit: {effective_shegavati_limit}")
            adjusted_amount, updated_used, sxva_shegavati = compute_adjusted_amount(
                total_debit, is_special, shegavati_used, effective_shegavati_limit, partner
            )
            amounts_tax, amounts_pension = fetch_tax_and_pension_amounts(
                adjusted_amount, is_special, sxva_shegavati
            )
            partner_shegavati_usage[partner.id] = updated_used

            first_name, surname = split_full_name(partner.name)
            address, country_name = get_partner_address_and_country(partner)
            country_code = country_code_map.get(country_name, 'N/A')

            pir_category = '4' if ref_line.account_id.code == '3130' else '26'
            ganacemis_saxe = '1' if ref_line.account_id.code == '3130' else '7'

            row_by_header = {
                'საიდენტიფიკაციო ნომერი': partner.vat,
                'მიმღების სახელი': first_name,
                'მიმღების გვარი': surname,
                'მისამართი': address,
                'რეზიდენტობა': country_code,
                'კატეგორია': pir_category,
                'განაცემის სახე': ganacemis_saxe,
                'განაცემი თანხა': adjusted_amount,
                'სხვა შეღავათები': sxva_shegavati,
                'for testing': total_debit,
                'საპენსიო': amounts_pension,
                'საშემოსავლო': amounts_tax,
                'გაცემის თარიღი': line_date.strftime('%d.%m.%Y'),
                'განაკვეთი': '20',
                'გათავისუფლებული': 0,
                'ჩათვლას დაქვემდებარებული': 0,
            }
            for col, header in enumerate(headers):
                worksheet.write(row, col, row_by_header.get(header, ''))
            row += 1

        workbook.close()
        output.seek(0)

        filename = f"journal_entry_report_{start_date}_to_{end_date}.xlsx"
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}'),
            ],
        )