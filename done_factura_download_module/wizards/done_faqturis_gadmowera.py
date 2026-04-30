from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse as date_parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

_logger = logging.getLogger(__name__)

# Max range for get_user_invoices (RS protocol)
GET_USER_INVOICES_DAYS = 3
# Parallel chunk requests and connection reuse
CHUNK_REQUEST_WORKERS = 12
REQUEST_TIMEOUT = 20
# Invoices per batch; 2*BATCH_SIZE concurrent line+doc HTTP requests per batch
BATCH_SIZE = 8


def _elem_text(elem, tag, default=''):
    if elem is None:
        return default
    child = elem.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    # try without namespace
    for c in elem:
        if c.tag.endswith(tag) or (c.tag.split('}')[-1] == tag if '}' in c.tag else c.tag == tag):
            return (c.text or '').strip()
    return default


def _parse_date(s):
    if not s:
        return None
    try:
        dt = date_parse(s)
        return dt.date() if hasattr(dt, 'date') else dt
    except Exception:
        return None


# Georgian month names (ოპერაციის თარიღიდან)
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


def _operation_date_to_georgian_month(date_val):
    """Convert a date to Georgian month name string, e.g. 'იანვარი 2025'."""
    if not date_val:
        return ''
    if hasattr(date_val, 'month') and hasattr(date_val, 'year'):
        month_name = GEORGIAN_MONTHS.get(date_val.month, '')
        return f'{month_name} {date_val.year}' if month_name else str(date_val)
    return str(date_val)


class DoneFaqturisGadmowera(models.TransientModel):
    _name = 'done.faqturis.gadmowera'
    _description = 'Done FAQTURI by agree_date (get_user_invoices)'

    date1 = fields.Date(string='პერიოდის დასაწყისი', required=True, default=fields.Date.today)
    date2 = fields.Date(string='პერიოდის დასასრული', required=True, default=fields.Date.today)
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)

    @api.depends()
    def _compute_rs_acc(self):
        for record in self:
            record.rs_acc = getattr(self.env.user, 'rs_acc', None) or ''

    @api.depends()
    def _compute_rs_pass(self):
        for record in self:
            record.rs_pass = getattr(self.env.user, 'rs_pass', None) or ''

    @api.constrains('date1', 'date2')
    def _check_date_range(self):
        for record in self:
            if record.date1 and record.date2:
                start = fields.Date.from_string(record.date1)
                end = fields.Date.from_string(record.date2)
                if end < start:
                    raise ValidationError('დასასრულის თარიღი არ უნდა იყოს საწყისზე ადრე.')
                delta = (end - start).days
                if delta > 29:
                    raise ValidationError(
                        'პერიოდი არ უნდა აღემატებოდეს 30 დღეს. '
                        'მაგალითად, 1 იანვარზე შეგიძლიათ აირჩიოთ 30 იანვარი ან უფრო ადრე.'
                    )

    def _find_text_by_local_name(self, root, local_name):
        """Find first element with given local tag name (ignoring namespace) and return its text."""
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == local_name and elem.text:
                return elem.text.strip()
        return None

    def rs_un_id(self, rs_acc, rs_pass):
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <chek_service_user xmlns="http://tempuri.org/">
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
    </chek_service_user>
  </soap:Body>
</soap:Envelope>"""
        try:
            response = requests.post(url, data=body, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            _logger.warning("rs_un_id request failed: %s", e)
            return None, None
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            _logger.warning("rs_un_id parse error: %s", e)
            return None, None
        un_id = self._find_text_by_local_name(root, 'un_id')
        s_user_id = self._find_text_by_local_name(root, 's_user_id')
        if not un_id:
            _logger.warning("rs_un_id: no un_id in response (length %s)", len(response.text))
        return un_id, s_user_id

    def chek(self, rs_acc, rs_pass):
        un_id, _ = self.rs_un_id(rs_acc, rs_pass)
        if not un_id:
            return None
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "http://tempuri.org/chek"}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <chek xmlns="http://tempuri.org/">
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
      <user_id>{un_id}</user_id>
    </chek>
  </soap:Body>
</soap:Envelope>"""
        try:
            response = requests.post(url, headers=headers, data=body, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            _logger.warning("chek request failed: %s", e)
            return None
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            _logger.warning("chek parse error: %s", e)
            return None
        user_id = self._find_text_by_local_name(root, 'user_id')
        if not user_id:
            _logger.warning("chek: no user_id in response (length %s)", len(response.text))
        return user_id

    def _get_user_invoices_chunk(self, last_start, last_end, user_id, un_id, rs_acc, rs_pass, session=None):
        """Call get_user_invoices for a 3-day (or less) range. Returns list of dicts."""
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_user_invoices",
        }
        start_str = last_start.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(last_start, datetime) else str(last_start) + 'T00:00:00'
        end_str = last_end.strftime('%Y-%m-%dT%H:%M:%S') if isinstance(last_end, datetime) else str(last_end) + 'T23:59:59'
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_user_invoices xmlns="http://tempuri.org/">
      <last_update_date_s>{start_str}</last_update_date_s>
      <last_update_date_e>{end_str}</last_update_date_e>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
      <user_id>{user_id}</user_id>
      <un_id>{un_id}</un_id>
    </get_user_invoices>
  </soap:Body>
</soap:Envelope>"""
        post = session.post if session else requests.post
        response = post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            _logger.warning("get_user_invoices failed: %s", response.text[:500])
            return []
        return self._parse_get_user_invoices_response(response.text)

    def _parse_get_user_invoices_response(self, response_text):
        """Extract invoice rows from get_user_invoices SOAP response."""
        root = ET.fromstring(response_text)
        rows = []
        for parent in root.iter():
            row = {}
            for c in parent:
                k = c.tag.split('}')[-1] if '}' in c.tag else c.tag
                row[k] = (c.text or '').strip()
            inv_id = row.get('Id') or row.get('ID')
            if inv_id and len(row) > 2:
                rows.append(row)
        for i, row in enumerate(rows):
            saident_no_s = row.get('saident_no_s') or row.get('saident_no_S') or row.get('SaidentNoS') or row.get('SAIDENT_NO_S') or ''
            saident_no_b = row.get('saident_no_b') or row.get('saident_no_B') or row.get('SaidentNoB') or row.get('SAIDENT_NO_B') or ''
            _logger.info("get_user_invoices row[%s] SAIDENT_NO_S=%s SAIDENT_NO_B=%s", i, saident_no_s, saident_no_b)
        return rows

    def send_soap_request(self):
        self.ensure_one()
        if not self.date1 or not self.date2:
            raise ValidationError('შეავსეთ პერიოდის თარიღები.')
        start = fields.Date.from_string(self.date1)
        end = fields.Date.from_string(self.date2)
        if (end - start).days > 29:
            raise ValidationError('პერიოდი არ უნდა აღემატებოდეს 30 დღეს.')

        rs_acc = self.rs_acc or getattr(self.env.user, 'rs_acc', None)
        rs_pass = self.rs_pass or getattr(self.env.user, 'rs_pass', None)
        if not rs_acc or not rs_pass:
            raise ValidationError('RS მომხმარებელი/პაროლი არ არის მითითებული.')

        un_id, _ = self.rs_un_id(rs_acc, rs_pass)
        user_id = self.chek(rs_acc, rs_pass)
        if not un_id or not user_id:
            raise ValidationError('RS ავტორიზაცია ვერ შესრულდა.')

        company_vat_raw = (self.env.company.vat or '').strip().replace(' ', '')
        if not company_vat_raw:
            raise ValidationError('მიმდინარე კომპანიის VAT არ არის მითითებული.')
        company_vat_normalized = company_vat_raw.upper()
        if company_vat_normalized.startswith('GE'):
            company_vat_normalized = company_vat_normalized[2:].lstrip()
        _logger.info("კომპანიის საიდენტიფიკატო ნომერი: %s", company_vat_normalized)
        all_rows = []
        chunk_start = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())
        chunks = []
        while chunk_start <= end_dt:
            chunk_end = min(chunk_start + timedelta(days=GET_USER_INVOICES_DAYS - 1), end_dt)
            chunks.append((chunk_start, chunk_end))
            chunk_start = chunk_end + timedelta(seconds=1)

        session = requests.Session()
        try:
            def fetch_chunk(args):
                c_start, c_end = args
                return self._get_user_invoices_chunk(
                    c_start, c_end, user_id, un_id, rs_acc, rs_pass, session=session
                )
            with ThreadPoolExecutor(max_workers=min(CHUNK_REQUEST_WORKERS, len(chunks) or 1)) as executor:
                futures = [executor.submit(fetch_chunk, (c_start, c_end)) for c_start, c_end in chunks]
                for future in as_completed(futures):
                    try:
                        chunk_rows = future.result()
                        for r in chunk_rows:
                            all_rows.append(r)
                    except Exception as e:
                        _logger.warning("Chunk fetch failed: %s", e)
        finally:
            pass  # keep session open for invoice loop below

        # Deduplicate by Id
        seen_ids = set()
        unique_rows = []
        for r in all_rows:
            inv_id = r.get('Id') or r.get('ID') or r.get('id')
            if inv_id and inv_id not in seen_ids:
                seen_ids.add(inv_id)
                unique_rows.append(r)

        # Filter by agree_date in [date1, date2]
        filtered = []
        for r in unique_rows:
            agree_val = r.get('agree_date') or r.get('AGREE_DATE') or r.get('Agree_Date') or ''
            if not agree_val:
                continue
            agree_d = _parse_date(agree_val)
            if agree_d is None:
                continue
            if start <= agree_d <= end:
                filtered.append(r)

        _logger.info("get_user_invoices: %s rows after agree_date filter", len(filtered))

        # Build list of (inv_id, create_vals) for rows that pass buyer + company VAT
        to_create = []
        skip_reasons = Counter()
        _logger.info("მონაცემები: %s", filtered)
        for row in filtered:
            inv_id = row.get('Id') or row.get('ID') or row.get('id') or ''
            if not inv_id:
                skip_reasons['missing_invoice_id'] += 1
                continue
            existing = self.env['done.factura'].search([('invoice_id', '=', inv_id)], limit=1)
            if existing:
                skip_reasons['already_exists'] += 1
                continue

            agree_date_val = _parse_date(row.get('agree_date') or row.get('AGREE_DATE') or row.get('Agree_Date'))
            operation_dt = row.get('operation_dt') or row.get('OPERATION_DT') or row.get('Operation_dt') or ''
            reg_dt = row.get('reg_dt') or row.get('REG_DT') or row.get('Reg_dt') or ''
            f_series = row.get('f_series') or row.get('F_SERIES') or ''
            f_number = row.get('f_number') or row.get('F_NUMBER') or ''
            tanxa = row.get('tanxa') or row.get('TANXA') or row.get('Tanxa') or '0'
            status = row.get('status') or row.get('STATUS') or row.get('Status') or '0'
            seller_un_id = row.get('seller_un_id') or row.get('Seller_un_id') or row.get('seller_un_Id') or ''
            buyer_un_id = row.get('buyer_un_id') or row.get('BUYER_UN_ID') or row.get('Buyer_un_id') or ''
            saident_no_s = (
                row.get('SAIDENT_NO_S') or row.get('saident_no_S') or ''
            )
            _logger.info("|||||||||saident_no_s: %s", saident_no_s)
            saident_no_b = (
                row.get('SAIDENT_NO_B') or row.get('saident_no_B') or
                row.get('SaidentNoB') or row.get('SAIDENT_NO_B') or ''
            )
            if not saident_no_b:
                for k, v in row.items():
                    if v and isinstance(k, str) and 'b' in k.lower() and 'ident' in k.lower():
                        saident_no_b = v
                        break

            try:
                status_int = int(status) if str(status).isdigit() else 0
            except Exception:
                status_int = 0

            waybill_type = 'seller' if str(seller_un_id) == str(un_id) else 'buyer'
            if waybill_type != 'buyer':
                skip_reasons['not_buyer_waybill'] += 1
                continue

            buyer_tin_raw = (saident_no_b or '').strip().replace(' ', '')
            if buyer_tin_raw.upper().startswith('GE'):
                buyer_tin_raw = buyer_tin_raw[2:].lstrip()
            buyer_tin = buyer_tin_raw.upper()
            if not buyer_tin or buyer_tin != company_vat_normalized:
                skip_reasons['buyer_tin_mismatch_or_missing'] += 1
                continue

            sa_ident_no = saident_no_s or ''
            # Resolve organization (seller): search res.partner by vat == SAIDENT_NO_S
            organization_id = False
            if sa_ident_no:
                saident_s = str(sa_ident_no).strip()
                if saident_s:
                    partner = self.env['res.partner'].search([('vat', '=', saident_s)], limit=1)
                    if partner:
                        organization_id = partner.id

            op_date = _parse_date(operation_dt) or agree_date_val or fields.Date.today()
            reg_date = _parse_date(reg_dt) or op_date
            operation_date_str = _operation_date_to_georgian_month(op_date)

            to_create.append((inv_id, {
                'invoice_id': inv_id,
                'series': f_series or 'N/A',
                'number': str(f_number) if f_number else 'N/A',
                'registration_date': reg_date,
                'operation_date': operation_date_str,
                'agree_date': agree_date_val,
                'organization_id': organization_id,
                'sa_ident_no': sa_ident_no,
                'tanxa': str(tanxa),
                'vat': 0.0,
                'buyer_un_id': str(buyer_un_id),
                'status': status_int,
                'waybill_type': waybill_type,
            }))

        if not to_create:
            _logger.warning(
                "No done.factura records created. Reasons=%s | total_rows=%s unique_rows=%s filtered_rows=%s company_vat=%s",
                dict(skip_reasons),
                len(all_rows),
                len(unique_rows),
                len(filtered),
                company_vat_normalized,
            )

        try:
            created_count = 0
            workers = min(2 * BATCH_SIZE, max(4, len(to_create) * 2))
            for i in range(0, len(to_create), BATCH_SIZE):
                batch = to_create[i:i + BATCH_SIZE]
                records = self.env['done.factura'].create([vals for _, vals in batch])
                created_count += len(records)
                inv_id_to_record = {inv_id: rec for (inv_id, _), rec in zip(batch, records)}

                with ThreadPoolExecutor(max_workers=workers) as pool:
                    lines_futures = [
                        pool.submit(self._fetch_invoice_lines_data, inv_id, user_id, rs_acc, rs_pass, session)
                        for inv_id, _ in batch
                    ]
                    docs_futures = [
                        pool.submit(self._fetch_invoice_documents_data, inv_id, user_id, rs_acc, rs_pass, session)
                        for inv_id, _ in batch
                    ]
                    lines_results = [f.result() for f in lines_futures]
                    docs_results = [f.result() for f in docs_futures]

                lines_map = {inv_id: data for inv_id, data in lines_results}
                docs_map = {inv_id: doc_data for inv_id, doc_data in docs_results}

                for inv_id, done_record in inv_id_to_record.items():
                    self._create_lines_from_data(done_record, lines_map.get(inv_id, []))
                    vat_sum = sum(ld.get('DRG_AMOUNT', 0) for ld in lines_map.get(inv_id, []))
                    done_record.write({'vat': vat_sum})
                    doc_data = docs_map.get(inv_id)
                    if doc_data:
                        no, date_val = doc_data
                        self.env['done.faqtura.document'].create({
                            'done_factura_id': done_record.id,
                            'document_number': no,
                            'date': date_val,
                        })
            if created_count == 0:
                _logger.warning(
                    "No done.factura records persisted after create stage. candidates=%s reasons=%s",
                    len(to_create),
                    dict(skip_reasons),
                )
        finally:
            session.close()

        return {'type': 'ir.actions.act_window_close'}

    def _update_header_vat_from_lines(self, done_record):
        """Set header vat = sum of line DRG_AMOUNT (დღგ-ს თანხა)."""
        total_vat = sum(line.DRG_AMOUNT for line in done_record.line_ids)
        done_record.write({'vat': total_vat})

    def _fetch_invoice_lines_data(self, invoice_id, user_id, rs_acc, rs_pass, session):
        """Thread-safe: HTTP + parse only. Returns (invoice_id, list of line dicts)."""
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "http://tempuri.org/get_invoice_desc"}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_invoice_desc xmlns="http://tempuri.org/">
      <user_id>{user_id}</user_id>
      <invois_id>{invoice_id}</invois_id>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
    </get_invoice_desc>
  </soap:Body>
</soap:Envelope>"""
        try:
            response = session.post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
        except Exception:
            return (invoice_id, [])
        if response.status_code != 200:
            return (invoice_id, [])
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return (invoice_id, [])

        def g(line_el, n):
            for c in line_el:
                t = c.tag.split('}')[-1] if '}' in c.tag else c.tag
                if t.upper() == n.upper():
                    return (c.text or '').strip()
            return ''

        line_ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1'}
        lines_found = []
        for path in ('.//diffgr:diffgram//DocumentElement/invoices_descs', './/DocumentElement/invoices_descs', './/invoices_descs'):
            try:
                lines_found = root.findall(path, line_ns)
            except Exception:
                lines_found = []
            if lines_found:
                break
        if not lines_found:
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag and tag != 'invoices_descs' and any((c.tag.split('}')[-1] if '}' in c.tag else c.tag).upper() == 'GOODS' for c in elem):
                    lines_found.append(elem)

        out = []
        for line_el in lines_found:
            goods = g(line_el, 'GOODS') or g(line_el, 'goods')
            g_number = float(g(line_el, 'G_NUMBER') or g(line_el, 'g_number') or 0)
            full_amount = float(g(line_el, 'FULL_AMOUNT') or g(line_el, 'full_amount') or 0)
            drg_amount = float(g(line_el, 'DRG_AMOUNT') or g(line_el, 'drg_amount') or 0)
            if not goods and full_amount == 0:
                continue
            out.append({
                'GOODS': goods, 'G_UNIT': g(line_el, 'G_UNIT') or g(line_el, 'g_unit'),
                'G_NUMBER': g_number, 'FULL_AMOUNT': full_amount,
                'price_unit': (full_amount / g_number) if g_number else full_amount,
                'DRG_AMOUNT': drg_amount,
                'AKCIS_ID': int(g(line_el, 'AKCIS_ID') or g(line_el, 'akcis_id') or 0),
                'VAT_TYPE': int(g(line_el, 'VAT_TYPE') or g(line_el, 'vat_type') or 0),
                'SDRG_AMOUNT': float(g(line_el, 'SDRG_AMOUNT') or g(line_el, 'sdrg_amount') or 0),
            })
        return (invoice_id, out)

    def _fetch_invoice_documents_data(self, invoice_id, user_id, rs_acc, rs_pass, session):
        """Thread-safe: HTTP + parse only. Returns (invoice_id, (document_number, date) or None)."""
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "http://tempuri.org/get_ntos_invoices_inv_nos"}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_ntos_invoices_inv_nos xmlns="http://tempuri.org/">
      <user_id>{user_id}</user_id>
      <invois_id>{invoice_id}</invois_id>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
    </get_ntos_invoices_inv_nos>
  </soap:Body>
</soap:Envelope>"""
        try:
            response = session.post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
        except Exception:
            return (invoice_id, None)
        if response.status_code != 200:
            return (invoice_id, None)
        try:
            root = ET.fromstring(response.content.decode('utf-8'))
        except Exception:
            return (invoice_id, None)
        overhead_no = overhead_dt_str = None
        for elem in root.iter():
            t = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if t == 'OVERHEAD_NO':
                overhead_no = (elem.text or '').strip()
            elif t == 'OVERHEAD_DT_STR':
                overhead_dt_str = (elem.text or '').strip()
        if not overhead_no or not overhead_dt_str:
            return (invoice_id, None)
        date_val = _parse_date(overhead_dt_str) or fields.Date.today()
        return (invoice_id, (overhead_no, date_val))

    def _create_lines_from_data(self, done_record, lines_data):
        """Create line records from pre-fetched data; bulk create and batch product resolution."""
        if not lines_data:
            return
        unique_goods = {ld.get('GOODS') or '' for ld in lines_data if ld.get('GOODS')}
        product_map = {}
        if unique_goods:
            for name in unique_goods:
                if not name:
                    continue
                p = self.env['product.product'].search([('name', 'ilike', name)], limit=1)
                if p:
                    product_map[name] = p.id
        line_vals = []
        for ld in lines_data:
            goods = ld.get('GOODS', '')
            line_vals.append({
                'done_factura_id': done_record.id,
                'product_id': product_map.get(goods) or False,
                'GOODS': goods,
                'G_UNIT': ld.get('G_UNIT', ''),
                'G_NUMBER': ld.get('G_NUMBER', 0),
                'FULL_AMOUNT': ld.get('FULL_AMOUNT', 0),
                'price_unit': ld.get('price_unit', 0),
                'DRG_AMOUNT': ld.get('DRG_AMOUNT', 0),
                'AKCIS_ID': ld.get('AKCIS_ID', 0),
                'VAT_TYPE': ld.get('VAT_TYPE', 0),
                'SDRG_AMOUNT': ld.get('SDRG_AMOUNT', 0),
            })
        if line_vals:
            self.env['done.faqtura.line'].create(line_vals)

    def _fetch_invoice_lines(self, done_record, user_id, rs_acc, rs_pass, session=None):
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "http://tempuri.org/get_invoice_desc"}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_invoice_desc xmlns="http://tempuri.org/">
      <user_id>{user_id}</user_id>
      <invois_id>{done_record.invoice_id}</invois_id>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
    </get_invoice_desc>
  </soap:Body>
</soap:Envelope>"""
        post = session.post if session else requests.post
        response = post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            _logger.warning("get_invoice_desc failed for %s: %s", done_record.invoice_id, response.status_code)
            return
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            _logger.warning("get_invoice_desc parse error for %s: %s", done_record.invoice_id, e)
            return

        def g(line_el, n):
            for c in line_el:
                t = c.tag.split('}')[-1] if '}' in c.tag else c.tag
                if t.upper() == n.upper():
                    return (c.text or '').strip()
            return ''

        line_namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
        }
        lines_found = []
        for path in (
            './/diffgr:diffgram//DocumentElement/invoices_descs',
            './/DocumentElement/invoices_descs',
            './/invoices_descs',
        ):
            try:
                lines_found = root.findall(path, line_namespaces)
            except Exception:
                lines_found = []
            if lines_found:
                break
        if not lines_found:
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if not tag or tag == 'invoices_descs':
                    continue
                if any((c.tag.split('}')[-1] if '}' in c.tag else c.tag).upper() == 'GOODS' for c in elem):
                    lines_found.append(elem)

        for line_el in lines_found:
            goods = g(line_el, 'GOODS') or g(line_el, 'goods')
            g_number = float(g(line_el, 'G_NUMBER') or g(line_el, 'g_number') or 0)
            full_amount = float(g(line_el, 'FULL_AMOUNT') or g(line_el, 'full_amount') or 0)
            drg_amount = float(g(line_el, 'DRG_AMOUNT') or g(line_el, 'drg_amount') or 0)
            if not goods and full_amount == 0:
                continue
            price_unit = (full_amount / g_number) if g_number else full_amount
            product = None
            if goods:
                product = self.env['product.product'].search([('name', 'ilike', goods)], limit=1)
            try:
                self.env['done.faqtura.line'].create({
                    'done_factura_id': done_record.id,
                    'product_id': product.id if product else False,
                    'GOODS': goods,
                    'G_UNIT': g(line_el, 'G_UNIT') or g(line_el, 'g_unit'),
                    'G_NUMBER': g_number,
                    'FULL_AMOUNT': full_amount,
                    'price_unit': price_unit,
                    'DRG_AMOUNT': drg_amount,
                    'AKCIS_ID': int(g(line_el, 'AKCIS_ID') or g(line_el, 'akcis_id') or 0),
                    'VAT_TYPE': int(g(line_el, 'VAT_TYPE') or g(line_el, 'vat_type') or 0),
                    'SDRG_AMOUNT': float(g(line_el, 'SDRG_AMOUNT') or g(line_el, 'sdrg_amount') or 0),
                })
            except Exception as e:
                _logger.warning("Skip line for invoice %s: %s", done_record.invoice_id, e)

    def _fetch_invoice_documents(self, done_record, user_id, rs_acc, rs_pass, session=None):
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "http://tempuri.org/get_ntos_invoices_inv_nos"}
        body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <get_ntos_invoices_inv_nos xmlns="http://tempuri.org/">
      <user_id>{user_id}</user_id>
      <invois_id>{done_record.invoice_id}</invois_id>
      <su>{rs_acc}</su>
      <sp>{rs_pass}</sp>
    </get_ntos_invoices_inv_nos>
  </soap:Body>
</soap:Envelope>"""
        post = session.post if session else requests.post
        response = post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return
        try:
            root = ET.fromstring(response.content.decode('utf-8'))
        except Exception:
            return
        overhead_no = None
        overhead_dt_str = None
        for elem in root.iter():
            t = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if t == 'OVERHEAD_NO':
                overhead_no = (elem.text or '').strip()
            elif t == 'OVERHEAD_DT_STR':
                overhead_dt_str = (elem.text or '').strip()
        if overhead_no and overhead_dt_str:
            date_val = _parse_date(overhead_dt_str) or fields.Date.today()
            self.env['done.faqtura.document'].create({
                'done_factura_id': done_record.id,
                'document_number': overhead_no,
                'date': date_val,
            })
