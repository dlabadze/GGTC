from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import xml.etree.ElementTree as ET
import logging
import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import datetime
_logger = logging.getLogger(__name__)

class FaqturisGadmoweraRealizacia(models.TransientModel):
    _name = 'faqturis.gadmowera.realizacia'
    _description = 'FAQTURI GADMO WERA REALIZACIA'

    date1 = fields.Date(string='პერიოდის დასაწყისი', required=True, default=fields.Date.today)
    date2 = fields.Date(string='პერიოდის დასასრული', required=True, default=fields.Date.today)
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    
    def _get_month_selection(self):
        months = [
            ('1', 'JANUARY'),
            ('2', 'FEBRUARY'),
            ('3', 'MARCH'),
            ('4', 'APRIL'),
            ('5', 'MAY'),
            ('6', 'JUNE'),
            ('7', 'JULY'),
            ('8', 'AUGUST'),
            ('9', 'SEPTEMBER'),
            ('10', 'OCTOBER'),
            ('11', 'NOVEMBER'),
            ('12', 'DECEMBER')
        ]
        return months

    selected_month = fields.Selection(
        selection='_get_month_selection',
        string='არჩეული თვე',
        required=True,
        default=str(fields.Date.today().month)
    )

    @api.depends()  
    def _compute_rs_acc(self):
        for record in self:
            record.rs_acc = self.env.user.rs_acc

    @api.depends()  
    def _compute_rs_pass(self):
        for record in self:
            record.rs_pass = self.env.user.rs_pass

    @api.constrains('date1', 'date2')
    def _check_date_range(self):
        for record in self:
            if record.date1 and record.date2:
                start_date = fields.Date.from_string(record.date1)
                end_date = fields.Date.from_string(record.date2)
                delta = end_date - start_date
                #if delta.days > 30:
                #    raise ValidationError('The end date must be within 30 days of the start date.')

    def send_soap_request(self):
        _logger.info("Executing send_soap_request with dates: %s - %s", self.date1, self.date2)

        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        start_date = self.date1
        end_date = self.date2
        selected_month_number = int(self.selected_month)
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
    
        # Determine the year based on the selected month
        if selected_month_number > current_month:
            year = current_year - 1
        else:
            year = current_year

            # Calculate month start and end
        month_start = datetime(year, selected_month_number, 1)
        month_end = month_start + relativedelta(months=1, days=-1)
    
        # Format dates for the SOAP request
        month_start_str = month_start.strftime('%Y-%m-%d')
        month_end_str = month_end.strftime('%Y-%m-%d')



        # Get un_id and s_user_id using the rs_un_id method
        _logger.info("Getting un_id and s_user_id for account: %s", rs_acc)
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)

        # Get user_id using the chek method
        _logger.info("Getting user_id for account: %s", rs_acc)
        user_id = self.chek(rs_acc, rs_pass)

        # Prepare your SOAP request
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_seller_invoices"
        }

        body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_seller_invoices xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <un_id>{un_id}</un_id>
                  <s_dt>{start_date}T00:00:00</s_dt>
                  <e_dt>{end_date}T23:59:59</e_dt>
                  <op_s_dt>{month_start_str}T00:00:00</op_s_dt>
                  <op_e_dt>{month_end_str}T23:59:59</op_e_dt>
                  <invoice_no></invoice_no>
                  <sa_ident_no></sa_ident_no>
                  <desc></desc>
                  <doc_mos_nom></doc_mos_nom>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </get_seller_invoices>
              </soap:Body>
            </soap:Envelope>"""

        _logger.info("Sending SOAP request to %s", url)
        response = requests.post(url, headers=headers, data=body)

        if response.status_code == 200:
            _logger.info("SOAP request successful: %s", response.text)
            self._process_response(response.text)  # Process the response
        else:
            _logger.error("SOAP request failed with status %s: %s", response.status_code, response.text)

    def _process_response(self, response_text):
        root = ET.fromstring(response_text)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
            'xmlns': '',
        }
    
        invoice_paths = [
            './/diffgr:diffgram//DocumentElement/invoices',
            './/diffgr:diffgram//invoices',
            './/DocumentElement/invoices',
            './/invoices'
        ]
    
        invoices = []
        for path in invoice_paths:
            invoices = root.findall(path, namespaces)
            if invoices:
                break
    
        if not invoices:
            _logger.error("No invoices found in the response")
            return
    
        invoice_data = []
        
        for invoice in invoices:
            invoice_info = {
                'Invoice ID': invoice.find('ID').text if invoice.find('ID') is not None else '',
                'Series': invoice.find('F_SERIES').text if invoice.find('F_SERIES') is not None else '',
                'Number': invoice.find('F_NUMBER').text if invoice.find('F_NUMBER') is not None else '',
                'Registration Date': invoice.find('REG_DT').text if invoice.find('REG_DT') is not None else '',
                'Operation Date': invoice.find('OPERATION_DT').text if invoice.find('OPERATION_DT') is not None else '',
                'Organization Name': invoice.find('ORG_NAME').text if invoice.find('ORG_NAME') is not None else '',
                'TANXA': invoice.find('TANXA').text if invoice.find('TANXA') is not None else '',
                'VAT': invoice.find('VAT').text if invoice.find('VAT') is not None else '',
                'Buyer UN ID': invoice.find('BUYER_UN_ID').text if invoice.find('BUYER_UN_ID') is not None else '',
                'sa_ident_no': invoice.find('SA_IDENT_NO').text if invoice.find('SA_IDENT_NO') is not None else '',
                'status': invoice.find('STATUS').text if invoice.find('STATUS') is not None else '',
            }
            
            _logger.info("Processing Invoice: %s", invoice_info)
            invoice_data.append(invoice_info)
        
        df_invoices = pd.DataFrame(invoice_data)
        
        for index, row in df_invoices.iterrows():
            waybill_type = 'seller'  # Adjust this based on your logic
        
            # Check if the invoice already exists in the system
            existing_invoice = self.env['faqturi'].search([('invoice_id', '=', row['Invoice ID'])], limit=1)
        
            if existing_invoice:
                _logger.info("Invoice ID %s already exists. Skipping creation.", row['Invoice ID'])
                continue  # Skip to the next invoice
        
            # Create a new invoice if it doesn't exist
            faqturi_record = self.env['faqturi'].create({
                'invoice_id': row['Invoice ID'],
                'series': row['Series'],
                'number': row['Number'],
                'registration_date': row['Registration Date'],
                'operation_date': row['Operation Date'],
                'organization_name': row['Organization Name'],
                'tanxa': row['TANXA'],
                'vat': row['VAT'],
                'buyer_un_id': row['Buyer UN ID'],
                'sa_ident_no': row['sa_ident_no'],
                'status': row['status'],
                'waybill_type': waybill_type,
            })
        
            _logger.info("Created new Invoice ID: %s", faqturi_record.invoice_id)

    # Fetch and process invoice lines...
    # (Rest of your existing logic for fetching and processing invoice lines)

            url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_invoice_desc"
            }
            
            user_id = self.chek(self.rs_acc, self.rs_pass)
    
            body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <get_invoice_desc xmlns="http://tempuri.org/">
                      <user_id>{user_id}</user_id>
                      <invois_id>{faqturi_record.invoice_id}</invois_id>
                      <su>{self.rs_acc}</su>
                      <sp>{self.rs_pass}</sp>
                    </get_invoice_desc>
                  </soap:Body>
                </soap:Envelope>"""
    
            response = requests.post(url, headers=headers, data=body)
            line_root = ET.fromstring(response.text)
            line_namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
                'xmlns': '',
            }
    
            line_paths = [
                './/diffgr:diffgram//DocumentElement/invoices_descs',
                './/diffgr:diffgram//invoices_descs',
                './/DocumentElement/invoices_descs',
                './/invoices_descs'
            ]
    
            lines = []
            for path in line_paths:
                lines = line_root.findall(path, line_namespaces)
                if lines:
                    break
    
            if not lines:
                _logger.error(f"No invoice lines found for Invoice ID: {faqturi_record.invoice_id}")
                continue
    
            for line in lines:
                try:
                    self.env['faqtura.line'].create({
                        'faqturi_id': faqturi_record.id,
                        'GOODS': line.find('GOODS').text if line.find('GOODS') is not None else '',
                        'G_UNIT': line.find('G_UNIT').text if line.find('G_UNIT') is not None else '',
                        'G_NUMBER': float(line.find('G_NUMBER').text) if line.find('G_NUMBER') is not None else 0.0,
                        'FULL_AMOUNT': float(line.find('FULL_AMOUNT').text) if line.find('FULL_AMOUNT') is not None else 0.0,
                        'DRG_AMOUNT': float(line.find('DRG_AMOUNT').text) if line.find('DRG_AMOUNT') is not None else 0.0,
                        'AKCIS_ID': int(line.find('AKCIS_ID').text) if line.find('AKCIS_ID') is not None else 0,
                        'VAT_TYPE': int(line.find('VAT_TYPE').text) if line.find('VAT_TYPE') is not None else 0,
                        'SDRG_AMOUNT': float(line.find('SDRG_AMOUNT').text) if line.find('SDRG_AMOUNT') is not None else 0.0,
                    })
                except Exception as e:
                    _logger.error(f"Error creating faqtura.line: {e}")
                    continue
    
            _logger.info("Processed invoice lines for Invoice ID: %s", faqturi_record.invoice_id)
    
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_ntos_invoices_inv_nos xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <invois_id>{faqturi_record.invoice_id}</invois_id>
                  <su>{self.rs_acc}</su>
                  <sp>{self.rs_pass}</sp>
                </get_ntos_invoices_inv_nos>
              </soap:Body>
            </soap:Envelope>"""
            
            # Request headers
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_ntos_invoices_inv_nos",
            }
            
            # Send SOAP request
            response = requests.post(
                "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx",
                data=soap_body,
                headers=headers
            )
            response_content = response.content.decode('utf-8')
            
            
            # Parse the XML string
            root = ET.fromstring(response_content)
            
            # Find the OVERHEAD_NO and OVERHEAD_DT_STR elements
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1'
            }
            
            
            overhead_no_elem = root.find('.//ntos_invoices_inv_nos/OVERHEAD_NO', namespaces)
            overhead_dt_str_elem = root.find('.//ntos_invoices_inv_nos/OVERHEAD_DT_STR', namespaces)
            
            overhead_no = overhead_no_elem.text if overhead_no_elem is not None else None
            overhead_dt_str = overhead_dt_str_elem.text if overhead_dt_str_elem is not None else None
            
            # Create a pandas DataFrame
            df = pd.DataFrame({
                'OVERHEAD_NO': [overhead_no],
                'OVERHEAD_DT_STR': [overhead_dt_str]
            })
            
            # Convert the 'OVERHEAD_DT_STR' column from DD.MM.YYYY to Odoo datetime format
            if 'OVERHEAD_DT_STR' in df and df['OVERHEAD_DT_STR'].notnull().any():
                try:
                    # Convert the date string to Odoo datetime format
                    df['OVERHEAD_DT_STR'] = pd.to_datetime(df['OVERHEAD_DT_STR'], format='%d.%m.%Y')
                    # Format it to the required string format for Odoo datetime
                    df['OVERHEAD_DT_STR'] = df['OVERHEAD_DT_STR'].dt.strftime('%Y-%m-%d 00:00:00')  # Set time to 00:00:00
                    _logger.info("Converted date format in DataFrame: %s", df)
                except Exception as e:
                    _logger.error("Date conversion error for Invoice ID %s: %s", faqturi_record.invoice_id, e)
            
            # Extract the converted values
            overhead_no = df['OVERHEAD_NO'].iloc[0] if not df['OVERHEAD_NO'].isnull().all() else None
            overhead_dt_str = df['OVERHEAD_DT_STR'].iloc[0] if not df['OVERHEAD_DT_STR'].isnull().all() else None
            
            # Check if we have both overhead_no and overhead_dt_str before creating the document record
            if overhead_no and overhead_dt_str:
                try:
                    # Create the document record
                    self.env['faqtura.document'].create({
                        'faqtura_line_id': faqturi_record.id,
                        'document_number': overhead_no,
                        'date': overhead_dt_str,
                    })
                    _logger.info("Created document record for Invoice ID: %s with Document Number: %s", faqturi_record.invoice_id, overhead_no)
                except Exception as e:
                    _logger.error("Error creating document record for Invoice ID %s: %s", faqturi_record.invoice_id, e)
            else:
                _logger.error("Failed to create document record for Invoice ID %s due to missing data", faqturi_record.invoice_id)

    



    def rs_un_id(self, rs_acc, rs_pass):
        _logger.info("Getting UN ID for account: %s", rs_acc)
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                          <soap:Body>
                            <chek_service_user xmlns="http://tempuri.org/">
                              <su>{rs_acc}</su>
                              <sp>{rs_pass}</sp>
                            </chek_service_user>
                          </soap:Body>
                        </soap:Envelope>"""

        response = requests.post(url, data=soap_body, headers=headers)
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }

        un_id_element = root.find('.//ns:un_id', namespaces)
        un_id = un_id_element.text if un_id_element is not None else None

        s_user_element = root.find('.//ns:s_user_id', namespaces)
        s_user_id = s_user_element.text if s_user_element is not None else None

        _logger.info("Obtained UN ID: %s, User ID: %s", un_id, s_user_id)
        return un_id, s_user_id

    def chek(self, rs_acc, rs_pass):
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/chek"
        }
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

        response = requests.post(url, headers=headers, data=body)
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        user_id_element = root.find('.//ns:user_id', namespaces)
        user_id = user_id_element.text if user_id_element is not None else None
        (_logger.info(user_id))
        return user_id



class FaqturisGadmoweraRealizaciaBuyer(models.TransientModel):
    _name = 'faqturis.gadmowera.realizacia.buyer'
    _description = 'FAQTURI GADMO WERA REALIZACIA BUYER'

    date1 = fields.Date(string='პერიოდის დასაწყისი', required=True, default=fields.Date.today)
    date2 = fields.Date(string='პერიოდის დასასრული', required=True, default=fields.Date.today)
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)

    def _get_month_selection(self):
        months = [
            ('1', 'JANUARY'),
            ('2', 'FEBRUARY'),
            ('3', 'MARCH'),
            ('4', 'APRIL'),
            ('5', 'MAY'),
            ('6', 'JUNE'),
            ('7', 'JULY'),
            ('8', 'AUGUST'),
            ('9', 'SEPTEMBER'),
            ('10', 'OCTOBER'),
            ('11', 'NOVEMBER'),
            ('12', 'DECEMBER')
        ]
        return months

    selected_month = fields.Selection(
        selection='_get_month_selection',
        string='არჩეული თვე',
        required=True,
        default=str(fields.Date.today().month)
    )

    @api.depends()
    def _compute_rs_acc(self):
        for record in self:
            record.rs_acc = self.env.user.rs_acc

    @api.depends()
    def _compute_rs_pass(self):
        for record in self:
            record.rs_pass = self.env.user.rs_pass

    @api.constrains('date1', 'date2')
    def _check_date_range(self):
        for record in self:
            if record.date1 and record.date2:
                start_date = fields.Date.from_string(record.date1)
                end_date = fields.Date.from_string(record.date2)
                delta = end_date - start_date
                #if delta.days > 30:
                #    raise ValidationError('The end date must be within 30 days of the start date.')

    def send_soap_request(self):
        _logger.info("Executing send_soap_request for buyer invoices with dates: %s - %s", self.date1, self.date2)

        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        start_date = self.date1
        end_date = self.date2
        selected_month_number = int(self.selected_month)
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        # Determine the year based on the selected month
        if selected_month_number > current_month:
            year = current_year - 1
        else:
            year = current_year

            # Calculate month start and end
        month_start = datetime(year, selected_month_number, 1)
        month_end = month_start + relativedelta(months=1, days=-1)

        # Format dates for the SOAP request
        month_start_str = month_start.strftime('%Y-%m-%d')
        month_end_str = month_end.strftime('%Y-%m-%d')

        # Get un_id and s_user_id using the rs_un_id method
        _logger.info("Getting un_id and s_user_id for account: %s", rs_acc)
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)

        # Get user_id using the chek method
        _logger.info("Getting user_id for account: %s", rs_acc)
        user_id = self.chek(rs_acc, rs_pass)

        # Prepare your SOAP request for buyer invoices
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_buyer_invoices"  # Update the SOAP action
        }

        body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_buyer_invoices xmlns="http://tempuri.org/">  <!-- Updated method -->
                  <user_id>{user_id}</user_id>
                  <un_id>{un_id}</un_id>
                  <s_dt>{start_date}T00:00:00</s_dt>
                  <e_dt>{end_date}T23:59:59</e_dt>
                  <op_s_dt>{month_start_str}T00:00:00</op_s_dt>
                  <op_e_dt>{month_end_str}T23:59:59</op_e_dt>
                  <invoice_no></invoice_no>
                  <sa_ident_no></sa_ident_no>
                  <desc></desc>
                  <doc_mos_nom></doc_mos_nom>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </get_buyer_invoices>
              </soap:Body>
            </soap:Envelope>"""

        _logger.info("Sending SOAP request to %s", url)
        response = requests.post(url, headers=headers, data=body)

        if response.status_code == 200:
            _logger.info("SOAP request successful: %s", response.text)
            self._process_response(response.text)  # Process the response
        else:
            _logger.error("SOAP request failed with status %s: %s", response.status_code, response.text)

    def _process_response(self, response_text):
        root = ET.fromstring(response_text)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
            'xmlns': '',
        }
    
        invoice_paths = [
            './/diffgr:diffgram//DocumentElement/invoices',
            './/diffgr:diffgram//invoices',
            './/DocumentElement/invoices',
            './/invoices'
        ]
    
        invoices = []
        for path in invoice_paths:
            invoices = root.findall(path, namespaces)
            if invoices:
                break
    
        if not invoices:
            _logger.error("No invoices found in the response")
            return
    
        invoice_data = []
        
    def _process_response(self, response_text):
        root = ET.fromstring(response_text)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
            'xmlns': '',
        }
    
        invoice_paths = [
            './/diffgr:diffgram//DocumentElement/invoices',
            './/diffgr:diffgram//invoices',
            './/DocumentElement/invoices',
            './/invoices'
        ]
    
        invoices = []
        for path in invoice_paths:
            invoices = root.findall(path, namespaces)
            if invoices:
                break
    
        if not invoices:
            _logger.error("No invoices found in the response")
            return
    
        invoice_data = []
        
        for invoice in invoices:
            invoice_info = {
                'Invoice ID': invoice.find('ID').text if invoice.find('ID') is not None else '',
                'Series': invoice.find('F_SERIES').text if invoice.find('F_SERIES') is not None else '',
                'Number': invoice.find('F_NUMBER').text if invoice.find('F_NUMBER') is not None else '',
                'Registration Date': invoice.find('REG_DT').text if invoice.find('REG_DT') is not None else '',
                'Operation Date': invoice.find('OPERATION_DT').text if invoice.find('OPERATION_DT') is not None else '',
                'Organization Name': invoice.find('ORG_NAME').text if invoice.find('ORG_NAME') is not None else '',
                'TANXA': invoice.find('TANXA').text if invoice.find('TANXA') is not None else '',
                'VAT': invoice.find('VAT').text if invoice.find('VAT') is not None else '',
                'Buyer UN ID': invoice.find('BUYER_UN_ID').text if invoice.find('BUYER_UN_ID') is not None else '',
                'sa_ident_no': invoice.find('SA_IDENT_NO').text if invoice.find('SA_IDENT_NO') is not None else '',
                'status': invoice.find('STATUS').text if invoice.find('STATUS') is not None else '',
            }
            
            _logger.info("Processing Invoice: %s", invoice_info)
            invoice_data.append(invoice_info)
        
        df_invoices = pd.DataFrame(invoice_data)
        
        for index, row in df_invoices.iterrows():
            waybill_type = 'buyer'  # Adjust this based on your logic
        
            # Check if the invoice already exists in the system
            existing_invoice = self.env['faqturi'].search([('invoice_id', '=', row['Invoice ID'])], limit=1)
        
            if existing_invoice:
                _logger.info("Invoice ID %s already exists. Skipping creation.", row['Invoice ID'])
                continue  # Skip to the next invoice
        
            # Create a new invoice if it doesn't exist
            faqturi_record = self.env['faqturi'].create({
                'invoice_id': row['Invoice ID'],
                'series': row['Series'],
                'number': row['Number'],
                'registration_date': row['Registration Date'],
                'operation_date': row['Operation Date'],
                'organization_name': row['Organization Name'],
                'tanxa': row['TANXA'],
                'vat': row['VAT'],
                'buyer_un_id': row['Buyer UN ID'],
                'sa_ident_no': row['sa_ident_no'],
                'status': row['status'],
                'waybill_type': waybill_type,
            })
        
            _logger.info("Created new Invoice ID: %s", faqturi_record.invoice_id)

    # Fetch and process invoice lines...
    # (Rest of your existing logic for fetching and processing invoice lines)

    
            _logger.info("Fetching line details for Invoice ID: %s", faqturi_record.invoice_id)
            url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_invoice_desc"
            }
            
            user_id = self.chek(self.rs_acc, self.rs_pass)
    
            body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                               xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                               xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <get_invoice_desc xmlns="http://tempuri.org/">
                      <user_id>{user_id}</user_id>
                      <invois_id>{faqturi_record.invoice_id}</invois_id>
                      <su>{self.rs_acc}</su>
                      <sp>{self.rs_pass}</sp>
                    </get_invoice_desc>
                  </soap:Body>
                </soap:Envelope>"""
    
            response = requests.post(url, headers=headers, data=body)
            line_root = ET.fromstring(response.text)
            line_namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
                'xmlns': '',
            }
    
            line_paths = [
                './/diffgr:diffgram//DocumentElement/invoices_descs',
                './/diffgr:diffgram//invoices_descs',
                './/DocumentElement/invoices_descs',
                './/invoices_descs'
            ]
    
            lines = []
            for path in line_paths:
                lines = line_root.findall(path, line_namespaces)
                if lines:
                    break
    
            if not lines:
                _logger.error(f"No invoice lines found for Invoice ID: {faqturi_record.invoice_id}")
                continue
    
            for line in lines:
                try:
                    self.env['faqtura.line'].create({
                        'faqturi_id': faqturi_record.id,
                        'GOODS': line.find('GOODS').text if line.find('GOODS') is not None else '',
                        'G_UNIT': line.find('G_UNIT').text if line.find('G_UNIT') is not None else '',
                        'G_NUMBER': float(line.find('G_NUMBER').text) if line.find('G_NUMBER') is not None else 0.0,
                        'FULL_AMOUNT': float(line.find('FULL_AMOUNT').text) if line.find('FULL_AMOUNT') is not None else 0.0,
                        'DRG_AMOUNT': float(line.find('DRG_AMOUNT').text) if line.find('DRG_AMOUNT') is not None else 0.0,
                        'AKCIS_ID': int(line.find('AKCIS_ID').text) if line.find('AKCIS_ID') is not None else 0,
                        'VAT_TYPE': int(line.find('VAT_TYPE').text) if line.find('VAT_TYPE') is not None else 0,
                        'SDRG_AMOUNT': float(line.find('SDRG_AMOUNT').text) if line.find('SDRG_AMOUNT') is not None else 0.0,
                    })
                except Exception as e:
                    _logger.error(f"Error creating faqtura.line: {e}")
                    continue
    
            _logger.info("Processed invoice lines for Invoice ID: %s", faqturi_record.invoice_id)
    
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_ntos_invoices_inv_nos xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <invois_id>{faqturi_record.invoice_id}</invois_id>
                  <su>{self.rs_acc}</su>
                  <sp>{self.rs_pass}</sp>
                </get_ntos_invoices_inv_nos>
              </soap:Body>
            </soap:Envelope>"""
            
            # Request headers
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_ntos_invoices_inv_nos",
            }
            
            # Send SOAP request
            response = requests.post(
                "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx",
                data=soap_body,
                headers=headers
            )
            response_content = response.content.decode('utf-8')
            
            
            # Parse the XML string
            root = ET.fromstring(response_content)
            
            # Find the OVERHEAD_NO and OVERHEAD_DT_STR elements
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1'
            }
            
            
            overhead_no_elem = root.find('.//ntos_invoices_inv_nos/OVERHEAD_NO', namespaces)
            overhead_dt_str_elem = root.find('.//ntos_invoices_inv_nos/OVERHEAD_DT_STR', namespaces)
            
            overhead_no = overhead_no_elem.text if overhead_no_elem is not None else None
            overhead_dt_str = overhead_dt_str_elem.text if overhead_dt_str_elem is not None else None
            
            # Create a pandas DataFrame
            df = pd.DataFrame({
                'OVERHEAD_NO': [overhead_no],
                'OVERHEAD_DT_STR': [overhead_dt_str]
            })
            
            # Convert the 'OVERHEAD_DT_STR' column from DD.MM.YYYY to Odoo datetime format
            if 'OVERHEAD_DT_STR' in df and df['OVERHEAD_DT_STR'].notnull().any():
                try:
                    # Convert the date string to Odoo datetime format
                    df['OVERHEAD_DT_STR'] = pd.to_datetime(df['OVERHEAD_DT_STR'], format='%d.%m.%Y')
                    # Format it to the required string format for Odoo datetime
                    df['OVERHEAD_DT_STR'] = df['OVERHEAD_DT_STR'].dt.strftime('%Y-%m-%d 00:00:00')  # Set time to 00:00:00
                    _logger.info("Converted date format in DataFrame: %s", df)
                except Exception as e:
                    _logger.error("Date conversion error for Invoice ID %s: %s", faqturi_record.invoice_id, e)
            
            # Extract the converted values
            overhead_no = df['OVERHEAD_NO'].iloc[0] if not df['OVERHEAD_NO'].isnull().all() else None
            overhead_dt_str = df['OVERHEAD_DT_STR'].iloc[0] if not df['OVERHEAD_DT_STR'].isnull().all() else None
            
            # Check if we have both overhead_no and overhead_dt_str before creating the document record
            if overhead_no and overhead_dt_str:
                try:
                    # Create the document record
                    self.env['faqtura.document'].create({
                        'faqtura_line_id': faqturi_record.id,
                        'document_number': overhead_no,
                        'date': overhead_dt_str,
                    })
                    _logger.info("Created document record for Invoice ID: %s with Document Number: %s", faqturi_record.invoice_id, overhead_no)
                except Exception as e:
                    _logger.error("Error creating document record for Invoice ID %s: %s", faqturi_record.invoice_id, e)
            else:
                _logger.error("Failed to create document record for Invoice ID %s due to missing data", faqturi_record.invoice_id)




    def rs_un_id(self, rs_acc, rs_pass):
        _logger.info("Getting UN ID for account: %s", rs_acc)
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                          <soap:Body>
                            <chek_service_user xmlns="http://tempuri.org/">
                              <su>{rs_acc}</su>
                              <sp>{rs_pass}</sp>
                            </chek_service_user>
                          </soap:Body>
                        </soap:Envelope>"""

        response = requests.post(url, data=soap_body, headers=headers)
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }

        un_id_element = root.find('.//ns:un_id', namespaces)
        un_id = un_id_element.text if un_id_element is not None else None

        s_user_element = root.find('.//ns:s_user_id', namespaces)
        s_user_id = s_user_element.text if s_user_element is not None else None

        _logger.info("Obtained UN ID: %s, User ID: %s", un_id, s_user_id)
        return un_id, s_user_id

    def chek(self, rs_acc, rs_pass):
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/chek"
        }
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

        response = requests.post(url, headers=headers, data=body)
        root = ET.fromstring(response.text)

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        user_id_element = root.find('.//ns:user_id', namespaces)
        user_id = user_id_element.text if user_id_element is not None else None
        (_logger.info(user_id))
        return user_id
