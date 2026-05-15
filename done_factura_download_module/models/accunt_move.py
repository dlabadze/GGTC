import logging
import requests
import xml.etree.ElementTree as ET
import re
from datetime import timedelta
from dateutil.parser import parse as date_parse
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

GEORGIAN_MONTHS = {
    1: 'იანვარი',
    2: 'თებერვალი',
    3: 'მარტი',
    4: 'აპრილი',
    5: 'მაისი',
    6: 'ივნისი',
    7: 'ივლისი',
    8: 'აგვისტო',
    9: 'სექტემბერი',
    10: 'ოქტომბერი',
    11: 'ნოემბერი',
    12: 'დეკემბერი',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    related_done_factura_ids = fields.Many2many(
        comodel_name='done.factura',
        relation='done_factura_account_move_rel',
        column1='account_move_id',
        column2='done_factura_id',
        string='Done ფაქტურები',
        copy=False,
    )
    factura_ids = fields.One2many('factura.checking', 'move_id', string='Factura Checks')
    rs_tanxa = fields.Float(
        string='RS Tanxa',
        compute='_compute_rs_tanxa',
        store=True,
    )
    factura_status = fields.Selection([
        ('0', 'დადასტურებული'),
        ('1', 'დაუდასტურებელი'),
        ('2', 'ვერ მოიძებნა'),
    ], string='Factura Status', copy=False)
    done_factura_date = fields.Date(
        string='Done Factura Date',
        compute='_compute_done_factura_date',
        store=True,
    )
    has_requisition_other_payment_condition = fields.Boolean(
        string='Has Requisition Other Payment Condition',
        compute='_compute_has_requisition_other_payment_condition',
    )

    @api.depends('related_done_factura_ids.agree_date')
    def _compute_done_factura_date(self):
        for record in self:
            dates = [d for d in record.related_done_factura_ids.mapped('agree_date') if d]
            if dates:
                record.done_factura_date = min(dates) + timedelta(days=10)
            else:
                record.done_factura_date = False

    @api.depends('factura_ids.rs_tanxa')
    def _compute_rs_tanxa(self):
        for record in self:
            record.rs_tanxa = sum(record.factura_ids.mapped('rs_tanxa'))

    @api.depends(
        'invoice_line_ids.purchase_line_id.order_id.requisition_id.payment_condition_ids.payment_condition',
        'purchase_id.requisition_id.payment_condition_ids.payment_condition',
    )
    def _compute_has_requisition_other_payment_condition(self):
        for record in self:
            record.has_requisition_other_payment_condition = bool(
                record._get_requisition_payment_condition_days('other')
            )

    def _xml_text_by_local_name(self, root, local_name):
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag_name == local_name and elem.text:
                return elem.text.strip()
        return None

    def _parse_date_safe(self, value):
        if not value:
            return None
        try:
            dt = date_parse(value)
            return dt.date() if hasattr(dt, 'date') else dt
        except Exception:
            return None

    def _operation_date_to_georgian_month(self, date_val):
        if not date_val:
            return ''
        if hasattr(date_val, 'month') and hasattr(date_val, 'year'):
            month_name = GEORGIAN_MONTHS.get(date_val.month, '')
            return f'{month_name} {date_val.year}' if month_name else str(date_val)
        return str(date_val)

    def _parse_get_user_invoices_response(self, response_text):
        rows = []
        try:
            root = ET.fromstring(response_text)
        except Exception:
            return rows
        for parent in root.iter():
            row = {}
            for c in parent:
                key = c.tag.split('}')[-1] if '}' in c.tag else c.tag
                row[key] = (c.text or '').strip()
            inv_id = row.get('Id') or row.get('ID') or row.get('id')
            if inv_id and len(row) > 2:
                rows.append(row)
        return rows

    def _normalize_factura_ref(self, value):
        """Normalize factura reference for tolerant matching."""
        return re.sub(r'[\s\-_/]', '', str(value or '').strip().upper())

    def _parse_amount_safe(self, value):
        """Parse RS amount strings like '1 234,56' safely."""
        if value in (None, False, ''):
            return 0.0
        txt = str(value).strip().replace('\xa0', '').replace(' ', '')
        txt = txt.replace(',', '.')
        txt = re.sub(r'[^0-9.\-]', '', txt)
        if not txt or txt in ('-', '.', '-.'):
            return 0.0
        try:
            return float(txt)
        except Exception:
            return 0.0

    def _fetch_invoice_total_from_desc(self, rs_invoice_id, user_id, rs_acc, rs_pass):
        """Fallback total from get_invoice_desc when header tanxa is zero."""
        # Reuse wizard parser: it is already battle-tested against RS response shapes.
        wizard_model = self.env['done.faqturis.gadmowera']
        session = requests.Session()
        try:
            _, lines_data = wizard_model._fetch_invoice_lines_data(
                rs_invoice_id, user_id, rs_acc, rs_pass, session
            )
            total_from_lines = sum((line.get('FULL_AMOUNT') or 0.0) for line in lines_data)
            if total_from_lines:
                return total_from_lines
        except Exception:
            _logger.exception("Failed tanxa fallback via get_invoice_desc lines parser")
        finally:
            session.close()

        # Secondary XML fallback for unexpected parser edge-cases.
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_invoice_desc",
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_invoice_desc xmlns="http://tempuri.org/">
      <user_id>{user_id}</user_id>
      <invois_id>{rs_invoice_id}</invois_id>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
    </get_invoice_desc>
  </soap:Body>
</soap:Envelope>"""
        try:
            response = requests.post(url, headers=headers, data=body, timeout=30)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception:
            return 0.0
        total = 0.0
        found_any = False
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag and tag.upper() == 'FULL_AMOUNT':
                amount = self._parse_amount_safe(elem.text)
                total += amount
                found_any = True
        return total if found_any else 0.0

    def _find_invoice_row_in_user_invoices(
        self,
        user_id,
        invoice_identifier=None,
        match_by='id',
        date_from=None,
        date_to=None,
        operation_dt=None,
        reg_dt=None,
    ):
        self.ensure_one()
        invoice_identifier = str(invoice_identifier or '').strip()
        if not invoice_identifier:
            return None
        normalized_invoice_identifier = self._normalize_factura_ref(invoice_identifier)

        rs_acc = (self.rs_acc or '').strip()
        rs_pass = (self.rs_pass or '').strip()
        un_id, _ = self.rs_un_id(rs_acc, rs_pass)
        if not un_id:
            return None

        if date_from and date_to:
            # Wizard dates are used as agree_date filter.
            # For RS request window, fetch changes from date_from up to now, then filter by agree_date in Python.
            start_dt = datetime.combine(date_from, datetime.min.time())
            end_dt = datetime.combine(fields.Date.today(), datetime.max.time())
        else:
            anchor_date = operation_dt or reg_dt or self.invoice_date or self.date or fields.Date.today()
            if isinstance(anchor_date, str):
                anchor_date = self._parse_date_safe(anchor_date) or fields.Date.today()
            # Default period:
            # start = anchor date - 30 days, end = today, with 3-day chunks.
            start_dt = datetime.combine(anchor_date - timedelta(days=30), datetime.min.time())
            end_dt = datetime.combine(fields.Date.today(), datetime.max.time())

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_user_invoices",
        }

        current = start_dt
        while current <= end_dt:
            chunk_end = min(current + timedelta(days=2), end_dt)  # RS max window = 3 days
            body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_user_invoices xmlns="http://tempuri.org/">
      <last_update_date_s>{current.strftime('%Y-%m-%dT%H:%M:%S')}</last_update_date_s>
      <last_update_date_e>{chunk_end.strftime('%Y-%m-%dT%H:%M:%S')}</last_update_date_e>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
      <user_id>{user_id}</user_id>
      <un_id>{un_id}</un_id>
    </get_user_invoices>
  </soap:Body>
</soap:Envelope>"""
            try:
                response = requests.post(url, headers=headers, data=body, timeout=30)
                if response.status_code == 200:
                    rows = self._parse_get_user_invoices_response(response.text)
                    for row in rows:
                        inv_id = row.get('Id') or row.get('ID') or row.get('id')
                        row_status = row.get('status') or row.get('STATUS') or row.get('Status')
                        agree_raw = row.get('agree_date') or row.get('AGREE_DATE') or row.get('Agree_Date')
                        row_f_number = row.get('f_number') or row.get('F_NUMBER') or row.get('f_Number')
                        row_f_series = row.get('f_series') or row.get('F_SERIES') or row.get('f_Series')
                        row_agree_date = self._parse_date_safe(agree_raw)
                        _logger.info(
                            "get_user_invoices row | factura_id=%s | status=%s | agree_date=%s | period=%s..%s",
                            inv_id,
                            row_status,
                            agree_raw,
                            current.strftime('%Y-%m-%d %H:%M:%S'),
                            chunk_end.strftime('%Y-%m-%d %H:%M:%S'),
                        )
                        if match_by == 'id':
                            is_match = str(inv_id or '').strip() == invoice_identifier
                        else:
                            f_series = str(row_f_series or '').strip()
                            f_number = str(row_f_number or '').strip()
                            candidate_values = {
                                f_number,
                                f'{f_series} {f_number}'.strip(),
                                f'{f_series}-{f_number}'.strip(),
                                f'{f_series}/{f_number}'.strip(),
                            }
                            normalized_candidates = {
                                self._normalize_factura_ref(c) for c in candidate_values if c
                            }
                            is_match = (
                                invoice_identifier in candidate_values
                                or normalized_invoice_identifier in normalized_candidates
                            )
                        if is_match:
                            if date_from and date_to:
                                if row_agree_date and date_from <= row_agree_date <= date_to:
                                    return row
                                _logger.info(
                                    "Invoice ID matched but agree_date out of range | factura_id=%s | agree_date=%s | filter=%s..%s",
                                    inv_id,
                                    row_agree_date,
                                    date_from,
                                    date_to,
                                )
                                return None
                            return row
            except Exception:
                _logger.exception("get_user_invoices chunk failed while resolving agree_date")
            current = chunk_end + timedelta(seconds=1)

        return None

    def _extract_done_factura_vals_from_root(
        self,
        root,
        status,
        user_id,
        invoice_identifier=None,
        forced_agree_date=None,
        date_from=None,
        date_to=None,
    ):
        self.ensure_one()

        invoice_identifier = str(invoice_identifier or '').strip()
        if not invoice_identifier:
            invoice_identifier = str(self.factura_num or '').strip()

        series = self._xml_text_by_local_name(root, 'f_series') or 'N/A'
        number = self._xml_text_by_local_name(root, 'f_number') or 'N/A'
        tanxa = (
            self._xml_text_by_local_name(root, 'tanxa')
            or self._xml_text_by_local_name(root, 'full_amount')
            or self.amount_total
            or 0.0
        )
        buyer_un_id = self._xml_text_by_local_name(root, 'buyer_un_id') or 'N/A'
        seller_un_id = self._xml_text_by_local_name(root, 'seller_un_id') or ''
        sa_ident_no = (
            self._xml_text_by_local_name(root, 'saident_no_s')
            or self._xml_text_by_local_name(root, 'saident_no')
            or ''
        )

        operation_dt = self._parse_date_safe(self._xml_text_by_local_name(root, 'operation_dt'))
        reg_dt = self._parse_date_safe(self._xml_text_by_local_name(root, 'reg_dt'))
        agree_date = forced_agree_date or self._parse_date_safe(self._xml_text_by_local_name(root, 'agree_date'))
        if not agree_date:
            row = self._find_invoice_row_in_user_invoices(
                user_id,
                invoice_identifier=invoice_identifier,
                match_by='f_number',
                date_from=date_from,
                date_to=date_to,
                operation_dt=operation_dt,
                reg_dt=reg_dt,
            )
            if row:
                agree_date = self._parse_date_safe(
                    row.get('agree_date') or row.get('AGREE_DATE') or row.get('Agree_Date')
                )
        if not agree_date:
            agree_date = self.invoice_date or self.date
        operation_date = operation_dt or agree_date or fields.Date.today()
        registration_date = reg_dt or operation_date

        organization_id = False
        if sa_ident_no:
            partner = self.env['res.partner'].search([('vat', '=', sa_ident_no.strip())], limit=1)
            if partner:
                organization_id = partner.id

        rs_acc = (self.rs_acc or '').strip()
        rs_pass = (self.rs_pass or '').strip()
        un_id, _ = self.rs_un_id(rs_acc, rs_pass)
        waybill_type = 'seller' if str(seller_un_id) and str(seller_un_id) == str(un_id) else 'buyer'

        return {
            'invoice_id': invoice_identifier,
            'series': series,
            'number': str(number),
            'registration_date': registration_date,
            'operation_date': self._operation_date_to_georgian_month(operation_date),
            'agree_date': agree_date,
            'organization_id': organization_id,
            'sa_ident_no': sa_ident_no,
            'tanxa': str(tanxa),
            'vat': 0.0,
            'buyer_un_id': str(buyer_un_id),
            'status': status,
            'waybill_type': waybill_type,
        }

    def _get_invoice_status_from_rs(self, invoice_identifier):
        self.ensure_one()

        invoice_identifier = str(invoice_identifier or '').strip()
        if not invoice_identifier:
            raise UserError(_('Factura Number (f_number) შევსებული არ არის.'))

        rs_acc = (self.rs_acc or '').strip()
        rs_pass = (self.rs_pass or '').strip()
        if not rs_acc or not rs_pass:
            raise UserError(_('RS მომხმარებელი ან პაროლი არ არის მითითებული.'))

        user_id = self.chek(rs_acc, rs_pass)
        if not user_id:
            raise UserError(_('RS ავტორიზაცია ვერ შესრულდა (user_id ვერ მოიძებნა).'))

        resolved_row = self._find_invoice_row_in_user_invoices(
            user_id,
            invoice_identifier=invoice_identifier,
            match_by='f_number',
        )
        rs_invoice_id = (
            (resolved_row or {}).get('Id')
            or (resolved_row or {}).get('ID')
            or (resolved_row or {}).get('id')
        )
        if not rs_invoice_id:
            raise UserError(_('RS-ში ფაქტურა ვერ მოიძებნა f_number-ით: %s') % invoice_identifier)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {'Content-Type': 'application/soap+xml; charset=utf-8'}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <get_invoice xmlns="http://tempuri.org/">
      <user_id>{user_id}</user_id>
      <invois_id>{rs_invoice_id}</invois_id>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
    </get_invoice>
  </soap12:Body>
</soap12:Envelope>"""

        try:
            response = requests.post(url, data=body, headers=headers, timeout=30)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except Exception as error:
            _logger.exception("Failed to fetch factura status from RS")
            raise UserError(_('RS-დან ფაქტურის მიღება ვერ მოხერხდა: %s') % error)

        status_raw = (
            self._xml_text_by_local_name(root, 'status')
            or self._xml_text_by_local_name(root, 'STATUS')
        )
        try:
            status = int(status_raw) if status_raw is not None else 0
        except Exception:
            status = 0

        series = self._xml_text_by_local_name(root, 'f_series')
        number = self._xml_text_by_local_name(root, 'f_number')
        # RS sometimes returns a status-like value even when the invoice does not exist.
        # Treat the invoice as found only if its identifying series/number is present.
        # _logger.info(f"აბა series: {type(series)} | number: {type(number)}")
        series_val = (series or '').strip()
        number_val = (number or '').strip()
        invoice_found = (
            series_val not in ('', '0')
            or number_val not in ('', '0')
        )
        tanxa_raw = (
            self._xml_text_by_local_name(root, 'tanxa')
            or self._xml_text_by_local_name(root, 'TANXA')
            or self._xml_text_by_local_name(root, 'full_amount')
            or self._xml_text_by_local_name(root, 'FULL_AMOUNT')
            or '0'
        )
        tanxa_value = self._parse_amount_safe(tanxa_raw)
        if tanxa_value == 0.0 and resolved_row:
            fallback_tanxa = (
                resolved_row.get('tanxa')
                or resolved_row.get('TANXA')
                or resolved_row.get('Tanxa')
                or resolved_row.get('full_amount')
                or resolved_row.get('FULL_AMOUNT')
                or resolved_row.get('Full_Amount')
            )
            tanxa_value = self._parse_amount_safe(fallback_tanxa)
        if tanxa_value == 0.0 and invoice_found:
            tanxa_value = self._fetch_invoice_total_from_desc(
                rs_invoice_id, user_id, rs_acc, rs_pass
            )
        return status, (series or 'N/A'), (number or 'N/A'), root, user_id, invoice_found, tanxa_value, str(rs_invoice_id)

    def _apply_account_line_analytics_to_done_lines(self, done_factura):
        """Link each done.faqtura.line to an account.move.line of this move and
        copy analytic_distribution / budget_analytic_id.

        Matching strategy (simple, deterministic):
          1) product_id equality (closest quantity if multiple).
          2) positional fallback: nth done line -> nth move line.
          3) last resort: first move line.
        """
        self.ensure_one()
        done_lines = done_factura.line_ids
        move_lines = self.env['account.move.line'].search([
            ('move_id', '=', self.id),
        ], order='id')
        if not done_lines or not move_lines:
            _logger.info(
                "Done factura analytic sync skipped: move=%s done_factura=%s done_lines=%s move_lines=%s",
                self.id, done_factura.id, len(done_lines), len(move_lines),
            )
            return

        # Find the fixed budget.analytic 'ხარჯები 2026' once.
        budget_analytic_2026 = self.env['budget.analytic'].search(
            [('name', '=', 'ხარჯები 2026')], limit=1
        )

        matched_count = 0
        used_ids = set()
        move_lines_list = list(move_lines)

        for index, done_line in enumerate(done_lines):
            candidate = self.env['account.move.line']

            if done_line.product_id:
                product_candidates = move_lines.filtered(
                    lambda ml: ml.product_id.id == done_line.product_id.id
                    and ml.id not in used_ids
                )
                if product_candidates:
                    candidate = product_candidates.sorted(
                        key=lambda ml: abs((ml.quantity or 0.0) - (done_line.G_NUMBER or 0.0))
                    )[:1]

            if not candidate and index < len(move_lines_list):
                positional = move_lines_list[index]
                if positional.id not in used_ids:
                    candidate = positional

            if not candidate:
                candidate = move_lines_list[0]

            used_ids.add(candidate.id)

            vals = {
                'account_move_line_id': candidate.id,
                'analytic_distribution': candidate.analytic_distribution or False,
                'budget_analytic_id': budget_analytic_2026.id if budget_analytic_2026 else False,
            }
            if not done_line.product_id and candidate.product_id:
                vals['product_id'] = candidate.product_id.id
            done_line.write(vals)
            matched_count += 1

        _logger.info(
            "Done factura analytic sync: move=%s done_factura=%s matched=%s/%s budget_analytic=%s",
            self.id, done_factura.id, matched_count, len(done_lines),
            budget_analytic_2026.name if budget_analytic_2026 else 'NOT FOUND',
        )

    def _fill_done_factura_lines_and_documents(self, done_factura, user_id, invoice_identifier):
        self.ensure_one()
        rs_acc = (self.rs_acc or '').strip()
        rs_pass = (self.rs_pass or '').strip()

        wizard_model = self.env['done.faqturis.gadmowera']
        session = requests.Session()
        try:
            _, lines_data = wizard_model._fetch_invoice_lines_data(
                invoice_identifier, user_id, rs_acc, rs_pass, session
            )
            wizard_model._create_lines_from_data(done_factura, lines_data)
            self._apply_account_line_analytics_to_done_lines(done_factura)
            vat_sum = sum(ld.get('DRG_AMOUNT', 0) for ld in lines_data)
            done_factura.write({'vat': vat_sum})

            _, doc_data = wizard_model._fetch_invoice_documents_data(
                invoice_identifier, user_id, rs_acc, rs_pass, session
            )
            if doc_data:
                no, date_val = doc_data
                self.env['done.faqtura.document'].create({
                    'done_factura_id': done_factura.id,
                    'document_number': no,
                    'date': date_val,
                })
        finally:
            session.close()

    def _move_has_requisition_avansi(self):
        self.ensure_one()
        po_model = self.env['purchase.order']
        req_model = self.env['purchase.requisition']
        if 'requisition_id' not in po_model._fields or 'avansi_ids' not in req_model._fields:
            return False
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')
        if 'purchase_id' in self._fields and self.purchase_id:
            purchase_orders |= self.purchase_id
        requisitions = purchase_orders.mapped('requisition_id').filtered(lambda r: r)
        has_avansi_condition = any(
            c.payment_condition == 'avansi'
            for r in requisitions
            for c in r.payment_condition_ids
        )
        return has_avansi_condition and bool(requisitions.mapped('avansi_ids'))

    def _get_linked_requisitions(self):
        self.ensure_one()
        po_model = self.env['purchase.order']
        if 'requisition_id' not in po_model._fields:
            return self.env['purchase.requisition']
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')
        if 'purchase_id' in self._fields and self.purchase_id:
            purchase_orders |= self.purchase_id
        return purchase_orders.mapped('requisition_id').filtered(lambda r: r)

    def _get_requisition_payment_condition_days(self, payment_condition_code):
        self.ensure_one()
        requisitions = self._get_linked_requisitions()
        conditions = requisitions.mapped('payment_condition_ids').filtered(
            lambda c: c.payment_condition == payment_condition_code
        )
        return conditions.mapped('days')

    def action_create_done_factura_from_other(self):
        self.ensure_one()
        requisitions = self._get_linked_requisitions()
        if not requisitions:
            raise UserError('ინვოისს არ აქვს PO-დან დაკავშირებული მოთხოვნა.')

        other_days = self._get_requisition_payment_condition_days('other')
        if not other_days:
            raise UserError('დაკავშირებულ მოთხოვნაზე გადახდის პირობებში "სხვა" არ არის მითითებული.')

        agree_date = self.invoice_date or self.date or fields.Date.today()
        done_vals = {
            'invoice_id': f'MOVE-{self.id}-OTHER',
            'series': 'MOVE',
            'number': (self.name or self.ref or str(self.id)),
            'registration_date': self.date or fields.Date.today(),
            'agree_date': agree_date,
            'arequisition_ids': [(6, 0, requisitions.ids)],
            'related_account_move_ids': [(4, self.id)],
            'organization_id': self.partner_id.id if self.partner_id else False,
            'status': 2,
        }
        done_vals['transfer_date'] = agree_date + timedelta(days=max(other_days))

        done_factura = self.env['done.factura'].create(done_vals)
        self.write({'related_done_factura_ids': [(4, done_factura.id)]})
        done_factura.sync_vendor_bills_from_requisitions()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Done ფაქტურა',
            'res_model': 'done.factura',
            'view_mode': 'form',
            'res_id': done_factura.id,
            'target': 'current',
        }

    def _get_invoice_check_requisition_avansi_vals(self, has_requisition_avansi):
        """Vals for done.factura from vendor bill check when PO/requisition has avansi lines."""
        self.ensure_one()
        po_model = self.env['purchase.order']
        req_model = self.env['purchase.requisition']
        if not has_requisition_avansi:
            return {
                'has_avansi': False,
                'arequisition_ids': [(5, 0, 0)],
                'requisition_avansi_id': False,
            }
        if 'requisition_id' not in po_model._fields or 'avansi_ids' not in req_model._fields:
            return {
                'has_avansi': False,
                'arequisition_ids': [(5, 0, 0)],
                'requisition_avansi_id': False,
            }
        purchase_orders = self.invoice_line_ids.mapped('purchase_line_id.order_id')
        if 'purchase_id' in self._fields and self.purchase_id:
            purchase_orders |= self.purchase_id
        requisitions = purchase_orders.mapped('requisition_id').filtered(lambda r: r and r.avansi_ids)
        if not requisitions:
            return {
                'has_avansi': False,
                'arequisition_ids': [(5, 0, 0)],
                'requisition_avansi_id': False,
            }
        all_avansi = requisitions.mapped('avansi_ids')
        chosen = all_avansi.sorted(
            key=lambda a: (a.date or fields.Date.from_string('1970-01-01'), a.id),
            reverse=True,
        )[:1]
        return {
            'has_avansi': 'invoice_avansi',
            'arequisition_ids': [(6, 0, requisitions.ids)],
            'requisition_avansi_id': chosen.id if chosen else False,
        }

    def action_open_check_done_factura_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('ფაქტურის შემოწმება'),
            'res_model': 'done.factura.check.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_date1': fields.Date.today() - timedelta(days=30),
                'default_date2': fields.Date.today(),
                'active_model': 'account.move',
                'active_ids': self.ids,
            }
        }

    def check_done_factura_in_period(self, date_from, date_to):
        done_model = self.env['done.factura']
        checked = 0
        created = 0
        not_found_in_period = 0

        for record in self:
            checked += 1
            all_not_found = True
            has_confirmed = False
            confirmed_payloads = []
            amount_total_confirmed = 0.0

            for factura_check in record.factura_ids:
                invoice_identifier = (factura_check.f_number or '').strip()
                if not invoice_identifier:
                    factura_check.write({'factura_status': '2', 'rs_tanxa': 0.0})
                    continue

                status, series, number, root, user_id, invoice_found, tanxa_value, rs_invoice_id = record._get_invoice_status_from_rs(
                    invoice_identifier
                )
                _logger.info(
                    "factura.checking | move=%s | f_number=%s | invoice_found=%s | status=%s | tanxa=%s",
                    record.id, invoice_identifier, invoice_found, status, tanxa_value
                )
                if not invoice_found:
                    factura_check.write({'factura_status': '2', 'rs_tanxa': 0.0})
                    continue

                all_not_found = False
                if status == 2:
                    has_confirmed = True
                    factura_check.write({'factura_status': '0', 'rs_tanxa': tanxa_value})
                    amount_total_confirmed += tanxa_value
                    confirmed_payloads.append({
                        'invoice_identifier': invoice_identifier,
                        'rs_invoice_id': rs_invoice_id,
                        'status': status,
                        'series': series,
                        'number': number,
                        'root': root,
                        'user_id': user_id,
                        'tanxa_value': tanxa_value,
                    })
                else:
                    # Keep RS amount even for non-confirmed invoice so user can see fetched value.
                    factura_check.write({'factura_status': '1', 'rs_tanxa': tanxa_value})

            if not record.factura_ids or all_not_found:
                record.write({
                    'related_done_factura_ids': [(5, 0, 0)],
                    'factura_status': '2',
                })
                continue

            rounding = record.currency_id.rounding or 0.01
            has_requisition_avansi = record._move_has_requisition_avansi()
            if (
                not has_confirmed
                or (
                    not has_requisition_avansi
                    and float_compare(amount_total_confirmed, record.amount_total, precision_rounding=rounding) != 0
                )
            ):
                record.write({
                    'related_done_factura_ids': [(5, 0, 0)],
                    'factura_status': '1',
                })
                continue

            payload_rows = []
            for payload in confirmed_payloads:
                user_invoice_row = record._find_invoice_row_in_user_invoices(
                    payload['user_id'],
                    invoice_identifier=payload['invoice_identifier'],
                    match_by='f_number',
                    date_from=date_from,
                    date_to=date_to,
                )
                if not user_invoice_row:
                    not_found_in_period += 1
                    continue

                agree_date_from_period = record._parse_date_safe(
                    user_invoice_row.get('agree_date')
                    or user_invoice_row.get('AGREE_DATE')
                    or user_invoice_row.get('Agree_Date')
                )
                payload_rows.append((payload, user_invoice_row, agree_date_from_period))

            if not payload_rows:
                record.write({
                    'related_done_factura_ids': [(5, 0, 0)],
                    'factura_status': '1',
                })
                continue

            # number uses all factura_ids on the move (not just confirmed in this period)
            all_f_numbers = [fc.f_number for fc in record.factura_ids if fc.f_number]
            number = all_f_numbers[0] if len(all_f_numbers) == 1 else 'N/A'
            agree_date = max((ad for _p, _r, ad in payload_rows if ad), default=record.invoice_date or record.date)

            combined_invoice_id = f'COMBINED-MOVE-{record.id}'
            combined_record = done_model.search([('invoice_id', '=', combined_invoice_id)], limit=1)
            combined_vals = {
                'invoice_id': combined_invoice_id,
                'series': 'N/A',
                'number': number,
                'registration_date': record.invoice_date or record.date or fields.Date.today(),
                'operation_date': record._operation_date_to_georgian_month(record.invoice_date or record.date),
                'agree_date': agree_date,
                'organization_id': record.partner_id.id if record.partner_id else False,
                'sa_ident_no': record.partner_id.vat if record.partner_id else False,
                'buyer_un_id': 'N/A',
                'status': 2,
                'waybill_type': 'buyer',
            }
            invoice_days = record._get_requisition_payment_condition_days('invoice')
            if combined_vals.get('agree_date') and invoice_days:
                combined_vals['transfer_date'] = combined_vals['agree_date'] + timedelta(days=max(invoice_days))
            combined_vals.update(record._get_invoice_check_requisition_avansi_vals(has_requisition_avansi))
            if not combined_record:
                combined_record = done_model.create(combined_vals)
                created += 1
            else:
                # Lines are accumulated across runs so tanxa grows with each confirmed factura
                combined_record.write(combined_vals)

            for payload, _user_row, _agree_date in payload_rows:
                record._fill_done_factura_lines_and_documents(
                    combined_record,
                    payload['user_id'],
                    payload['rs_invoice_id'],
                )

            vat_sum = sum(combined_record.line_ids.mapped('DRG_AMOUNT'))
            combined_record.write({
                'vat': vat_sum,
                **record._get_invoice_check_requisition_avansi_vals(has_requisition_avansi),
            })
            record._apply_account_line_analytics_to_done_lines(combined_record)

            combined_record.write({'related_account_move_ids': [(4, record.id)]})
            record.write({
                'factura_status': '0',
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('ფაქტურის შემოწმება დასრულდა'),
                'message': _(
                    'შემოწმდა: %(checked)s | შეიქმნა: %(created)s | არჩეულ პერიოდში ვერ მოიძებნა: %(not_found)s'
                ) % {
                    'checked': checked,
                    'created': created,
                    'not_found': not_found_in_period,
                },
                'type': 'warning' if not_found_in_period else 'success',
                'sticky': False,
            }
        }

    def check_done_factura(self):
        return self.check_done_factura_in_period(
            fields.Date.today() - timedelta(days=30),
            fields.Date.today(),
        )
    