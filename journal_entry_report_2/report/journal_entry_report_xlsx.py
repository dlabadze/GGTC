from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime
from collections import defaultdict


def compute_adjusted_amount(line, shegavati_used, shegavati_limit=3000):
    debit = line.debit or 0.0
    remaining = shegavati_limit - shegavati_used

    if remaining <= 0:
        adjusted = round(debit / (0.784 if line.partner_id.x_studio_ else 0.8), 2)
        return adjusted, shegavati_used, 0

    if debit <= remaining:
        adjusted = round(debit / (0.98 if line.partner_id.x_studio_ else 1), 2)
        return adjusted, shegavati_used + debit, debit

    taxable_part = debit - remaining
    adjusted_taxable = round(taxable_part / (0.784 if line.partner_id.x_studio_ else 0.8), 2)
    total_adjusted = round(remaining / (0.98 if line.partner_id.x_studio_ else 1), 2) + adjusted_taxable
    return total_adjusted, shegavati_used + remaining, remaining


def get_initial_shegavati_usage(partner, contact_start_date, start_date_dt, debits, credits, shegavati_limit=3000):
    shegavati_used = 0.0
    debit_credit = debits + credits

    lines = request.env['account.move.line'].search([
        ('date', '>=', contact_start_date),
        ('date', '<', start_date_dt),
        ('partner_id', '=', partner.id),
        ('account_id.code', 'in', debit_credit),
    ], order='date asc')

    debit_lines = [l for l in lines if l.debit > 0 and l.account_id.code in debits]
    credit_lines = [l for l in lines if l.credit > 0 and l.account_id.code in credits]
    used_credit_ids = set()

    for d in debit_lines:
        matched = False
        for c in credit_lines:
            if c.id in used_credit_ids:
                continue
            if d.account_id.code in debits and c.account_id.code in credits:
                remaining = shegavati_limit - shegavati_used
                if remaining <= 0:
                    return shegavati_limit
                debit_amount = d.debit
                if debit_amount <= remaining:
                    shegavati_used += debit_amount
                else:
                    shegavati_used += remaining
                used_credit_ids.add(c.id)
                matched = True
                break
        if not matched:
            continue

    return shegavati_used


class JournalEntryExcelReport(http.Controller):

    @http.route('/journal_entry_excel_2/download', type='http', auth='user')
    def download_excel_report(self, start_date, end_date, debit_ids, credit_ids):
        start_date_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

        debit_codes = []
        credit_codes = []
        if debit_ids:
            debit_codes = request.env['account.account'].browse([int(i) for i in debit_ids.split(',')]).mapped('code')
        if credit_ids:
            credit_codes = request.env['account.account'].browse([int(i) for i in credit_ids.split(',')]).mapped('code')

        all_relevant_debits = request.env['account.move.line'].search([
            ('date', '>=', start_date_dt),
            ('date', '<=', end_date_dt),
            ('debit', '>', 0),
            ('partner_id', '!=', False),
            ('account_id.code', 'in', debit_codes),
        ], order='date asc')

        matched_debit_lines = []
        used_debit_lines = set()
        used_credit_lines = set()

        for move in all_relevant_debits.mapped('move_id'):
            debit_lines = [
                l for l in move.line_ids
                if l.date >= start_date_dt and l.date <= end_date_dt
                and l.account_id.code in debit_codes and l.debit > 0
            ]
            credit_lines = [
                l for l in move.line_ids
                if l.date >= start_date_dt and l.date <= end_date_dt
                and l.account_id.code in credit_codes and l.credit > 0
            ]

            for d in debit_lines:
                if d.id in used_debit_lines:
                    continue
                for c in credit_lines:
                    if c.id in used_credit_lines:
                        continue
                    if abs(d.debit - c.credit) <= 0.01:
                        if d.account_id.code in debit_codes and c.account_id.code in credit_codes:
                            matched_debit_lines.append(d)
                            used_debit_lines.add(d.id)
                            used_credit_lines.add(c.id)
                            break

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Journal Entries')

        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        worksheet.set_column('A:M', 40)

        headers = [
            'საიდენტიფიკაციო ნომერი (პირადი ნომერი)',
            'თანხის მიმღების სახელი/სამართლებრივი ფორმა',
            'თანხის მიმღების გვარი/დასახელება',
            'მისამართი',
            'პირის რეზიდენტობა (ქვეყანა)',
            'შემოსავლის მიმღებ პირთა კატეგორია',
            'განაცემის სახე',
            'განაცემი თანხა (ლარი)',
            'სხვა შეღავათები',
            'for testing',
            'გაცემის თარიღი',
            'წყაროსთან დასაკავებელი გადასახადის განაკვეთი',
            'საერთაშორისო ხელშეკრულების საფუძველზე გათავისუფლებას ან შემცირებას დაქვემდებარებული გადასახადის თანხა',
            'ორმაგი დაბეგვრის თავიდან აცილების შესახებ ხელშეკრულების საფუძველზე ჩათვლას დაქვემდებარებული, უცხო ქვეყანაში გადახდილი გადასახადის თანხა,'
        ]

        for col, title in enumerate(headers):
            worksheet.write(0, col, title, header_format)

        partner_shegavati_usage = defaultdict(float)
        country_map_model = request.env['res.country.code.map.2']
        country_map = {
            rec.country_name.strip(): rec.country_code
            for rec in country_map_model.search([])
        }

        row = 1
        for line in matched_debit_lines:
            if line.account_id.code not in debit_codes:
                continue
            if not (start_date_dt <= line.date <= end_date_dt):
                continue

            partner_id = line.partner_id.id
            shegavati_limit = line.partner_id.x_studio_shegavati or 0.0
            partner = line.partner_id

            if partner_id not in partner_shegavati_usage:
                initial_used = get_initial_shegavati_usage(
                    partner, partner.x_studio_start_date_1, start_date_dt, debit_codes, credit_codes, shegavati_limit
                )
                partner_shegavati_usage[partner_id] = initial_used

            shegavati_used = partner_shegavati_usage[partner_id]
            adjusted_amount, updated_used, sxava_shegavati = compute_adjusted_amount(line, shegavati_used, shegavati_limit)
            partner_shegavati_usage[partner_id] = updated_used

            full_name = (line.partner_id.name or '').strip()
            parts = full_name.split()
            partner_name = parts[0] if parts else ''
            partner_surname = ' '.join(parts[1:]) if len(parts) > 1 else ''

            address = f"{line.partner_id.city or ''}, {line.partner_id.street or ''}"
            country_name = (line.partner_id.country_id.name or '').strip()
            code = country_map.get(country_name, 'N/A')

            if line.account_id.code == '3130':
                pir_category = '4'
                ganacemis_saxe = '1'
                ganakveti = '20'
            else:
                pir_category = '26'
                ganacemis_saxe = '7'
                ganakveti = '20'

            inter_contract = 0
            double_gross_rid = 0

            worksheet.write(row, 0, line.partner_id.vat)
            worksheet.write(row, 1, partner_name)
            worksheet.write(row, 2, partner_surname)
            worksheet.write(row, 3, address)
            worksheet.write(row, 4, code)
            worksheet.write(row, 5, pir_category)
            worksheet.write(row, 6, ganacemis_saxe)
            worksheet.write(row, 7, adjusted_amount)
            worksheet.write(row, 8, sxava_shegavati)
            worksheet.write(row, 9, line.debit)
            worksheet.write(row, 10, line.date.strftime('%d.%m.%Y'))
            worksheet.write(row, 11, ganakveti)
            worksheet.write(row, 12, inter_contract)
            worksheet.write(row, 13, double_gross_rid)
            row += 1

        workbook.close()
        output.seek(0)
        filename = f"journal_entry_report_2_{start_date}_to_{end_date}.xlsx"

        return request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', f'attachment; filename={filename}'),
            ]
        )

