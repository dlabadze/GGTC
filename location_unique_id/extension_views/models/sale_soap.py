from odoo import models, fields, api, _, exceptions
import requests
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError
import logging
from datetime import timezone, timedelta, datetime
import datetime




_logger = logging.getLogger(__name__)



#gana
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_name_from_tin(self,rs_acc, rs_pass, tin):
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <get_name_from_tin xmlns="http://tempuri.org/">
          <su>{rs_acc}</su>
          <sp>{rs_pass}</sp>
          <tin>{tin}</tin>
        </get_name_from_tin>
      </soap:Body>
    </soap:Envelope>"""

        # Define the URL and headers
        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_name_from_tin"
        }

        # Send the request
        response = requests.post(url, data=soap_request, headers=headers)

        # Comprehensive logging for get_name_from_tin
        _logger.info(f'=== GET_NAME_FROM_TIN REQUEST DETAILS ===')
        _logger.info(f'URL: {url}')
        _logger.info(f'Headers: {headers}')
        _logger.info(f'TIN: {tin}')
        _logger.info(f'Request Status Code: {response.status_code}')
        _logger.info(f'Response Headers: {dict(response.headers)}')
        _logger.info(f'Full SOAP Response Text: {response.text}')
        _logger.info(f'Response Length: {len(response.text)} characters')

        # Check if the request was successful
        if response.status_code == 200:
            # Extract the content of the get_name_from_tinResult element from the response
            start_tag = "<get_name_from_tinResult>"
            end_tag = "</get_name_from_tinResult>"
            start_index = response.text.find(start_tag) + len(start_tag)
            end_index = response.text.find(end_tag)
            name = response.text[start_index:end_index]
            # Fill the name field with the response
            _logger.info(f'✅ Successfully extracted name: {name}')
            return name
        else:
            _logger.error(f'❌ Failed to get name from TIN. Status code: {response.status_code}')
            _logger.error(f'Response: {response.text}')


    def generate_goods_list_xml(self, record):
        goods_list_xml = "<GOODS_LIST>"

        for line in self.order_line:
            product = line.product_id
            quantity = line.product_uom_qty
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)
            amount = line.price_total
            barcode = line.barcode
            unit_id = line.unit_id
            if not barcode:  # Check if the barcode is empty
                raise UserError(_('დაამატეთ ბარკოდი პროდუქციაზე'))
            if not unit_id:  # Check if the unit_id is empty
                raise UserError(_('დამატეთ rs.ge-ს ერთეული პროდუქციაზე'))
            tax_id = line.tax_id.name
            # Initialize vat_type to a default value
            vat_type = -1  # or any other default value
            if quantity != 0:
                price_unit = amount / quantity
            else:
                price_unit = 0
            unit_txt = line.unit_txt

            if tax_id == '18%':
                vat_type = 0
            elif tax_id =='0%':
                vat_type = 1
            else:
                raise UserError(_('დაბეგვრა უნდა იყოს ან 18 ან 0'))

            goods_xml = f"""
                <GOODS>
                    <ID>0</ID>
                    <W_NAME>{product.name}</W_NAME>
                    <UNIT_ID>{unit_id}</UNIT_ID>
                    <UNIT_TXT>{unit_txt}</UNIT_TXT>
                    <QUANTITY>{quantity}</QUANTITY>
                    <PRICE>{price_unit}</PRICE>
                    <STATUS>1</STATUS>
                    <AMOUNT>{amount}</AMOUNT>
                    <BAR_CODE>{barcode}</BAR_CODE>
                    <A_ID>0</A_ID>
                    <VAT_TYPE>{vat_type}</VAT_TYPE>
                </GOODS>
            """
            goods_list_xml += goods_xml

        goods_list_xml += "</GOODS_LIST>"
        return goods_list_xml


    @api.model
    def send_soap_request(self):
        goods_list_xml = self.generate_goods_list_xml(self)
        buyer_type = self.buyer_type
        start_location = self.start_location
        end_location = self.end_location
        driver_id = self.driver_id
        driver_type = self.driver_type
        driver_name = self.get_name_from_tin(self.rs_acc, self.rs_pass, driver_id)
        self.driver_name = driver_name
        transport_cost = self.transport_cost
        car_number = self.car_number
        transport_cost_payer = self.transport_cost_payer
        trans_id = self.trans_id
        delivery = self.delivery
        editable_end_location = self.editable_end_location
        comment = self.comment
        trans_txt = self.trans_txt
        now = datetime.now()
        begin_date = self.begin_date
        formatted_begin_date=self.formatted_begin_date
        buyer_name=self.partner_id
        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        completed_soap = self.completed_soap
        buyer_tin = self.partner_vat
        if self.combined_invoice_id:
            raise UserError("ზედნადები უკვე ატვირთულია")

        # Define the URL and headers
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

        # Send the request
        response = requests.post(url, data=soap_body, headers=headers)

        # _logger.info the response status code
        _logger.info(response.status_code)

        # Parse the XML response
        root = ET.fromstring(response.text)

        # Define the namespace (use the appropriate namespace for your SOAP response)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        # Find the `un_id` element in the response
        un_id_element = root.find('.//ns:un_id', namespaces)
        seller_un_id = un_id_element.text

        soap_request = f"""
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <save_waybill xmlns="http://tempuri.org/">
                    <su>{rs_acc}</su>
                    <sp>{rs_pass}</sp>
                    <waybill>
                        <WAYBILL xmlns="">
                            {goods_list_xml}
                            <ID>0</ID>
                            <TYPE>{delivery}</TYPE>
                            <BUYER_TIN>{buyer_tin}</BUYER_TIN>
                            <CHEK_BUYER_TIN>{buyer_type}</CHEK_BUYER_TIN>
                            <BUYER_NAME>{buyer_name}</BUYER_NAME>
                            <START_ADDRESS>{start_location}</START_ADDRESS>
                            <END_ADDRESS>{editable_end_location}</END_ADDRESS>
                            <DRIVER_TIN>{driver_id}</DRIVER_TIN>
                            <CHEK_DRIVER_TIN>{driver_type}</CHEK_DRIVER_TIN>
                            <DRIVER_NAME>{driver_name}</DRIVER_NAME>
                            <TRANSPORT_COAST>{transport_cost}</TRANSPORT_COAST>
                            <RECEPTION_INFO></RECEPTION_INFO>
                            <RECEIVER_INFO></RECEIVER_INFO>
                            <DELIVERY_DATE></DELIVERY_DATE>
                            <STATUS>1</STATUS>
                            <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                            <PAR_ID>0</PAR_ID>
                            <CAR_NUMBER>{car_number}</CAR_NUMBER>
                            <BEGIN_DATE>{formatted_begin_date}</BEGIN_DATE>
                            <TRAN_COST_PAYER>{transport_cost_payer}</TRAN_COST_PAYER>
                            <TRANS_ID>{trans_id}</TRANS_ID>
                            <TRANS_TXT>{trans_txt}</TRANS_TXT>
                            <COMMENT>{comment}</COMMENT>
                            <TRANSPORTER_TIN></TRANSPORTER_TIN>
                        </WAYBILL>
                    </waybill>
                </save_waybill>
            </soap:Body>
        </soap:Envelope>
        """

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_waybill"
        }

        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers)
        response_text = response.text

        # Comprehensive logging for debugging
        _logger.info(f'=== SOAP REQUEST DETAILS ===')
        _logger.info(f'URL: {url}')
        _logger.info(f'Headers: {headers}')
        _logger.info(f'Request Status Code: {response.status_code}')
        _logger.info(f'Response Headers: {dict(response.headers)}')
        _logger.info(f'Full SOAP Response Text: {response_text}')
        _logger.info(f'Response Length: {len(response_text)} characters')
        
        # Check for common response patterns
        _logger.info(f'=== RESPONSE ANALYSIS ===')
        _logger.info(f'Contains <STATUS>: {"<STATUS>" in response_text}')
        _logger.info(f'Contains </STATUS>: {"</STATUS>" in response_text}')
        _logger.info(f'Contains <soap:Envelope>: {"<soap:Envelope>" in response_text}')
        _logger.info(f'Contains <soap:Fault>: {"<soap:Fault>" in response_text}')
        _logger.info(f'Contains <faultstring>: {"<faultstring>" in response_text}')
        _logger.info(f'Contains <detail>: {"<detail>" in response_text}')
        
        # Log first 500 characters for quick inspection
        _logger.info(f'First 500 characters: {response_text[:500]}')
        
        # Extract Status with proper error handling
        try:
            if '<STATUS>' in response_text and '</STATUS>' in response_text:
                Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
                _logger.info(f'✅ Successfully extracted STATUS: {Status}')
            else:
                _logger.error(f'❌ No STATUS found in response')
                _logger.error(f'Full response for analysis: {response_text}')
                
                # Try to find any XML elements that might contain status information
                import re
                status_patterns = [
                    r'<STATUS[^>]*>(.*?)</STATUS>',
                    r'<status[^>]*>(.*?)</status>',
                    r'<Status[^>]*>(.*?)</Status>',
                    r'<result[^>]*>(.*?)</result>',
                    r'<Result[^>]*>(.*?)</Result>',
                ]
                
                for pattern in status_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    if matches:
                        _logger.info(f'Found potential status matches with pattern {pattern}: {matches}')
                
                raise UserError(f'Invalid response from server: No STATUS found. Response: {response_text[:200]}...')
        except IndexError:
            _logger.error(f'❌ Error parsing STATUS from response')
            _logger.error(f'Full response: {response_text}')
            raise UserError(f'Error parsing server response')


        if Status >= '0':
            pass

          ##  invoice_id = response_text.split('<ID>')[1].split('</ID>')[0]
            #invoice_number = response_text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]

            # Update current model fields
           # self.invoice_id = invoice_id
            #self.invoice_number = invoice_number
            #self.completed_soap = '1'

            # Create or update CombinedInvoiceModel record
            # Create new record if none exists
            #combined_invoice = self.env['combined.invoice.model'].create({
             #   'invoice_id': invoice_id,
              #  'invoice_number': invoice_number,
                # Add more fields if needed
            #})

            # Link the combined_invoice to current model
            #elf.combined_invoice_id = combined_invoice.id


        elif Status < '0':
            # Define the SOAP request XML with the provided <su> and <sp> values
            soap_request = f"""
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                    </get_error_codes>
                </soap:Body>
            </soap:Envelope>
            """

            # Define the headers
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_error_codes"
            }

            # Send the SOAP request
            response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx", data=soap_request, headers=headers)

            # Comprehensive logging for get_error_codes
            _logger.info(f'=== GET_ERROR_CODES REQUEST DETAILS ===')
            _logger.info(f'URL: http://services.rs.ge/waybillservice/waybillservice.asmx')
            _logger.info(f'Headers: {headers}')
            _logger.info(f'Request Status Code: {response.status_code}')
            _logger.info(f'Response Headers: {dict(response.headers)}')
            _logger.info(f'Full SOAP Response Text: {response.text}')
            _logger.info(f'Response Length: {len(response.text)} characters')

            if response.status_code == 200:
                # Parse the XML response
                root = ET.fromstring(response.content)

                # Define the namespaces
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'tempuri': 'http://tempuri.org/'
                }

                # Initialize an empty dictionary to store ID and TEXT values
                error_dict = {}

                # Find all ERROR_CODE elements and extract ID and TEXT values
                for error_code in root.findall(".//ERROR_CODE"):
                    id_value = error_code.find("ID").text
                    text_value = error_code.find("TEXT").text
                    error_dict[id_value] = text_value

                # Compare Status to numbers in error_dict and get corresponding error text
                error_text = error_dict.get(Status, "ამ სტატუსისთვის ერორი არ მოიძებნა შეამოწმე ექაუნთი და პაროლი rs.ge")
                self.error_field = error_text
                raise UserError(error_text)

    def button_send_soap_request(self):
        for record in self:
            record.send_soap_request()




class AccountMove(models.Model):
    _inherit = 'account.move'
    
    def get_name_from_tin(self, rs_acc, rs_pass, tin):
        """Get company name from TIN with comprehensive error handling"""
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <get_name_from_tin xmlns="http://tempuri.org/">
          <su>{rs_acc}</su>
          <sp>{rs_pass}</sp>
          <tin>{tin}</tin>
        </get_name_from_tin>
      </soap:Body>
    </soap:Envelope>"""

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_name_from_tin"
        }

        # Use safe request handler  
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"get_name_from_tin(TIN:{tin})"
        )
        
        if not success:
            _logger.error(f"get_name_from_tin failed: {error_msg}")
            return f"შეცდომა: {error_msg}"
        
        # Parse response safely
        name = self._parse_xml_response(
            response_text,
            './/ns:get_name_from_tinResult',
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
             'ns': 'http://tempuri.org/'}
        )
        
        if not name:
            # Try fallback extraction
            if '<get_name_from_tinResult>' in response_text:
                start_tag = "<get_name_from_tinResult>"
                end_tag = "</get_name_from_tinResult>"
                start_index = response_text.find(start_tag) + len(start_tag)
                end_index = response_text.find(end_tag)
                result = response_text[start_index:end_index].strip()
                
                # Check if it's a negative error code
                if result.startswith('-'):
                    error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
                    _logger.error(f"get_name_from_tin error: {error_text}")
                    return f"შეცდომა: {error_text}"
                
                return result if result else "უცნობი"
            
            _logger.error("get_name_from_tin: Response empty")
            return "უცნობი (ცარიელი პასუხი)"
        
        _logger.info(f'✅ Name from TIN {tin}: {name}')
        return name


    def generate_goods_list_xml(self):
        goods_list_xml = "<GOODS_LIST>"

        for line in self.invoice_line_ids:
            product = line.product_id

            # Skip if there is no product_id
            if not product:
                continue

            # Check if the product type is service
            if product.type == 'service':
                continue  # Skip this product

            quantity = line.quantity
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)

            price_unit = line.price_total / quantity if quantity != 0 else 0
            amount = line.price_total
            barcode = product.barcode
            unit_id = product.unit_id
            tax_id = line.tax_ids[0].name if line.tax_ids else ''  # Assuming tax_ids is a list
            unit_txt = product.unit_txt
            category_name = product.x_studio_catname.x_name

            # Initialize vat_type to a default value
            vat_type = -1  # or any other default value

            if tax_id == '18%':
                vat_type = 0
            elif tax_id == '0%':
                vat_type = 1

            goods_xml = f"""
                <GOODS>
                    <ID>0</ID>
                    <W_NAME>{category_name} {product.name}</W_NAME>
                    <UNIT_ID>{unit_id}</UNIT_ID>
                    <UNIT_TXT>{unit_txt}</UNIT_TXT>
                    <QUANTITY>{quantity}</QUANTITY>
                    <PRICE>{price_unit}</PRICE>
                    <STATUS>1</STATUS>
                    <AMOUNT>{amount}</AMOUNT>
                    <BAR_CODE>{barcode}</BAR_CODE>
                    <A_ID>0</A_ID>
                    <VAT_TYPE>{vat_type}</VAT_TYPE>
                </GOODS>
            """
            goods_list_xml += goods_xml

        goods_list_xml += "</GOODS_LIST>"
        return goods_list_xml


    def send_soap_request(self):
        try:
            goods_list_xml = self.generate_goods_list_xml()
            _logger.info('Goods List XML: %s', goods_list_xml)

            # Extracting required fields
            buyer_type = self.buyer_type
            start_location = self.start_location
            end_location = self.end_location
            driver_id = self.driver_id
            driver_type = self.driver_type
            driver_name = self.get_name_from_tin(self.rs_acc, self.rs_pass, driver_id)
            self.driver_name = driver_name
            transport_cost = self.transport_cost
            car_number = self.car_number
            transport_cost_payer = self.transport_cost_payer
            trans_id = self.trans_id
            delivery = self.delivery
            editable_end_location = self.editable_end_location
            comment = self.comment
            trans_txt = self.trans_txt
            now = datetime.now()
            begin_date = self.begin_date
            formatted_begin_date = self.formatted_begin_date
            buyer_name = self.partner_id.name
            buyer_tin = self.partner_vat
            rs_acc = self.rs_acc
            rs_pass = self.rs_pass

            _logger.info('Buyer Type: %s, Start Location: %s, End Location: %s', buyer_type, start_location, end_location)
            _logger.info('Driver ID: %s, Driver Type: %s, Driver Name: %s', driver_id, driver_type, driver_name)
            _logger.info('Transport Cost: %s, Car Number: %s, Transport Cost Payer: %s', transport_cost, car_number, transport_cost_payer)
            _logger.info('Transaction ID: %s, Delivery: %s, Editable End Location: %s', trans_id, delivery, editable_end_location)
            _logger.info('Comment: %s, Transaction Text: %s, Now: %s, Begin Date: %s, Formatted Begin Date: %s',
                         comment, trans_txt, now, begin_date, formatted_begin_date)
            _logger.info('Buyer Name: %s, Buyer TIN: %s', buyer_name, buyer_tin)
            _logger.info('Buyer Name: %s, Buyer TIN: %s', rs_acc, rs_pass)


            # First SOAP request to check service user
            url_check_service_user = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
            }
            soap_body_check_service_user = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek_service_user xmlns="http://tempuri.org/">
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </chek_service_user>
              </soap:Body>
            </soap:Envelope>"""

            # Send the request
            response_check_service_user = requests.post(url_check_service_user, data=soap_body_check_service_user.encode('utf-8'), headers=headers)
            _logger.info('First SOAP Response Status Code: %s', response_check_service_user.status_code)
            _logger.info(f'=== FIRST SOAP REQUEST DETAILS ===')
            _logger.info(f'URL: {url_check_service_user}')
            _logger.info(f'Headers: {headers}')
            _logger.info(f'Request Status Code: {response_check_service_user.status_code}')
            _logger.info(f'Response Headers: {dict(response_check_service_user.headers)}')
            _logger.info(f'Full SOAP Response Text: {response_check_service_user.text}')
            _logger.info(f'Response Length: {len(response_check_service_user.text)} characters')

            # Parse the XML response
            root_check_service_user = ET.fromstring(response_check_service_user.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
            }

            un_id_element = root_check_service_user.find('.//ns:un_id', namespaces)
            if un_id_element is not None:
                seller_un_id = un_id_element.text
                _logger.info('Seller UN ID: %s', seller_un_id)
            else:
                raise UserError("Unable to find 'un_id' in the response")

            # Second SOAP request to save waybill
            url_save_waybill = "http://services.rs.ge/waybillservice/waybillservice.asmx"
            soap_request_save_waybill = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <save_waybill xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                        <waybill>
                            <WAYBILL xmlns="">
                                {goods_list_xml}
                                <ID>0</ID>
                                <TYPE>{delivery}</TYPE>
                                <BUYER_TIN>{buyer_tin}</BUYER_TIN>
                                <CHEK_BUYER_TIN>{buyer_type}</CHEK_BUYER_TIN>
                                <BUYER_NAME>{buyer_name}</BUYER_NAME>
                                <START_ADDRESS>{start_location}</START_ADDRESS>
                                <END_ADDRESS>{editable_end_location}</END_ADDRESS>
                                <DRIVER_TIN>{driver_id}</DRIVER_TIN>
                                <CHEK_DRIVER_TIN>{driver_type}</CHEK_DRIVER_TIN>
                                <DRIVER_NAME>{driver_name}</DRIVER_NAME>
                                <TRANSPORT_COAST>{transport_cost}</TRANSPORT_COAST>
                                <RECEPTION_INFO></RECEPTION_INFO>
                                <RECEIVER_INFO></RECEIVER_INFO>
                                <DELIVERY_DATE></DELIVERY_DATE>
                                <STATUS>0</STATUS>
                                <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                                <PAR_ID>0</PAR_ID>
                                <CAR_NUMBER>{car_number}</CAR_NUMBER>
                                <BEGIN_DATE>{formatted_begin_date}</BEGIN_DATE>
                                <TRAN_COST_PAYER>{transport_cost_payer}</TRAN_COST_PAYER>
                                <TRANS_ID>{trans_id}</TRANS_ID>
                                <TRANS_TXT>{trans_txt}</TRANS_TXT>
                                <COMMENT>{comment}</COMMENT>
                                <TRANSPORTER_TIN></TRANSPORTER_TIN>
                            </WAYBILL>
                        </waybill>
                    </save_waybill>
                </soap:Body>
            </soap:Envelope>"""

            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/save_waybill"
            }

            # Send the request
            response_save_waybill = requests.post(url_save_waybill, data=soap_request_save_waybill.encode('utf-8'), headers=headers)
            _logger.info('Second SOAP Response Status Code: %s', response_save_waybill.status_code)
            _logger.info(f'=== SECOND SOAP REQUEST DETAILS ===')
            _logger.info(f'URL: {url_save_waybill}')
            _logger.info(f'Headers: {headers}')
            _logger.info(f'Request Status Code: {response_save_waybill.status_code}')
            _logger.info(f'Response Headers: {dict(response_save_waybill.headers)}')
            _logger.info(f'Full SOAP Response Text: {response_save_waybill.text}')
            _logger.info(f'Response Length: {len(response_save_waybill.text)} characters')

            # Parse the response to extract invoice ID and number
            if response_save_waybill.status_code == 200:
                response_text = response_save_waybill.text
                # Extract Status with proper error handling
                _logger.info(f'SOAP Response: {response_text}')
                try:
                    if '<STATUS>' in response_text and '</STATUS>' in response_text:
                        Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
                    else:
                        _logger.error(f'No STATUS found in response: {response_text}')
                        raise UserError(f'Invalid response from server: No STATUS found')
                except IndexError:
                    _logger.error(f'Error parsing STATUS from response: {response_text}')
                    raise UserError(f'Error parsing server response')

                if Status >= '0':
                    pass
                   # invoice_id = response_text.split('<ID>')[1].split('</ID>')[0]
                    #invoice_number = response_text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]

                    # Create or update CombinedInvoiceModel record
                    #combined_invoice = self.env['combined.invoice.model'].create({
                    #    'invoice_id': invoice_id,
                    #    'invoice_number': invoice_number,

                        # Add more fields if needed
                   # })

                    # Link the combined_invoice to current model
                    #self.combined_invoice_id = combined_invoice.id
                    # Update the sale order's combined_invoice_id if found
                    #if self.invoice_origin:
                     #   sale_order = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
                      #  if sale_order:
                       #     # Set the combined_invoice_id on the sale order
                        #    sale_order.combined_invoice_id = combined_invoice.id

                            # Update related deliveries with combined_invoice_id
                         #   deliveries = sale_order.picking_ids.filtered(lambda p: p.state not in ['cancel', 'done'])
                          #  for delivery in deliveries:
                           #     delivery.write({'combined_invoice_id': combined_invoice.id})


                elif Status < '0':
                    # Define the SOAP request XML with the provided <su> and <sp> values
                    soap_request = f"""
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                        <soap:Body>
                            <get_error_codes xmlns="http://tempuri.org/">
                                <su>{rs_acc}</su>
                                <sp>{rs_pass}</sp>
                            </get_error_codes>
                        </soap:Body>
                    </soap:Envelope>
                    """

                    # Define the headers
                    headers = {
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": "http://tempuri.org/get_error_codes"
                    }

                    # Send the SOAP request
                    response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx", data=soap_request, headers=headers)

                    if response.status_code == 200:
                        # Parse the XML response
                        root = ET.fromstring(response.content)

                        # Define the namespaces
                        namespaces = {
                            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                            'tempuri': 'http://tempuri.org/'
                        }

                        # Initialize an empty dictionary to store ID and TEXT values
                        error_dict = {}

                        # Find all ERROR_CODE elements and extract ID and TEXT values
                        for error_code in root.findall(".//ERROR_CODE"):
                            id_value = error_code.find("ID").text
                            text_value = error_code.find("TEXT").text
                            error_dict[id_value] = text_value

                        # Compare Status to numbers in error_dict and get corresponding error text
                        error_text = error_dict.get(Status, "No error found for this status")
                        self.error_field = error_text
                        raise UserError(error_text)
        except Exception as e:
            _logger.exception("Error occurred while sending SOAP request")
            raise UserError(f"Error: {e}")


    def button_send_soap_request(self):
        """Upload waybills - auto-detects single vs batch mode"""
        _logger.info(f'Executing button_send_soap_request for {len(self)} record(s)')
        
        # Single record mode - original behavior with page refresh
        if len(self) == 1:
            for record in self:
                if not record.invoice_id:
                    record.send_soap_request()
                else:
                    raise UserError('ზედნადები უკვე ატვირთლია')
        
        # Batch mode - process all records with error handling
        else:
            success_records = []
            error_records = []
            skipped_records = []
            
            for record in self:
                try:
                    if record.invoice_id:
                        skipped_records.append((record.name, 'ზედნადები უკვე ატვირთულია'))
                        continue
                        
                    record.send_soap_request()
                    success_records.append(record.name)
                    self.env.cr.commit()  # Commit after each successful record
                    
                except Exception as e:
                    error_records.append((record.name, str(e)))
                    self.env.cr.rollback()  # Rollback failed record
                    _logger.exception(f"Error processing waybill {record.name}")
            
            # Build result message
            messages = []
            if success_records:
                messages.append(f"✓ წარმატებით ატვირთულია ({len(success_records)}): {', '.join(success_records)}")
            if skipped_records:
                skipped_msg = '\n'.join([f"  - {name}: {reason}" for name, reason in skipped_records])
                messages.append(f"⊘ გამოტოვებულია ({len(skipped_records)}):\n{skipped_msg}")
            if error_records:
                error_msg = '\n'.join([f"  - {name}: {error}" for name, error in error_records])
                messages.append(f"✗ შეცდომები ({len(error_records)}):\n{error_msg}")
            
            final_message = '\n\n'.join(messages)
            
            if error_records and not success_records:
                raise UserError(final_message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ზედნადებების ატვირთვა დასრულდა'),
                    'message': final_message,
                    'type': 'success' if not error_records else 'warning',
                    'sticky': True,
                }
            }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def button_send_soap_request(self):
        for record in self:
            # Define the URL and headers
            url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
            }

            # Define the SOAP body
            usn = record.rs_acc  # Use the rs_acc field of the record
            usp = record.rs_pass  # Use the rs_pass field of the record

            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek_service_user xmlns="http://tempuri.org/">
                  <su>{usn}</su>
                  <sp>{usp}</sp>
                </chek_service_user>
              </soap:Body>
            </soap:Envelope>"""

            # Send the request
            response = requests.post(url, data=soap_body, headers=headers)

            # Parse the XML response
            root = ET.fromstring(response.text)

            # Define the namespace (use the appropriate namespace for your SOAP response)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
            }

            # Find the `un_id` element in the response
            un_id_element = root.find('.//ns:un_id', namespaces)

            # Check if the element was found and assign its text to the buyer_tin field
            if un_id_element is not None:
                record.buyer_tin = un_id_element.text

class ResPartner(models.Model):
    _inherit = 'res.partner'


    def button_get_name_from_tin(self):
        for record in self:
            try:
                usn = record.rs_acc  # Use the rs_acc field of the record
                usp = record.rs_pass  # Use the rs_pass field of the record
                tin = record.vat

                soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <get_name_from_tin xmlns="http://tempuri.org/">
                      <su>{usn}</su>
                      <sp>{usp}</sp>
                      <tin>{tin}</tin>
                    </get_name_from_tin>
                  </soap:Body>
                </soap:Envelope>"""

                # Define the URL and headers
                url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_name_from_tin"
                }

                # Send the request
                response = requests.post(url, data=soap_request, headers=headers)

                # Check for a successful response
                if response.status_code != 200:
                    record.company_review = f"Failed to get response from service. Status code: {response.status_code}"
                    continue

                # Parse the XML response
                root = ET.fromstring(response.text)

                # Define the namespace (use the appropriate namespace for your SOAP response)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
                }

                # Find the `name` element in the response
                result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

                # Check if the element was found and assign its text to the company_review field
                if result_element is not None:
                    record.name = result_element.text
                else:
                    _logger.error(f'Could not find get_name_from_tinResult in response')
                    record.company_review = "Could not find name in response"

            except Exception as e:
                record.company_review = f"An error occurred: {str(e)}"

class StockMove(models.Model):
    _inherit = 'stock.picking'

    # ... existing fields and methods ...

    # ============================================================================
    # HELPER METHODS FOR ERROR HANDLING
    # ============================================================================
    
    def _get_error_text_from_code(self, rs_acc, rs_pass, error_code):
        """
        Get human-readable error text from RS.GE error code
        
        Args:
            rs_acc: RS account username
            rs_pass: RS account password  
            error_code: Error code (negative number or string)
            
        Returns:
            str: Error message in Georgian
        """
        try:
            soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                    </get_error_codes>
                </soap:Body>
            </soap:Envelope>
            """
            
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_error_codes"
            }
            
            response = requests.post(
                "http://services.rs.ge/waybillservice/waybillservice.asmx",
                data=soap_request,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                return f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
            
            root = ET.fromstring(response.content)
            error_dict = {}
            
            for error_code_elem in root.findall(".//ERROR_CODE"):
                id_elem = error_code_elem.find("ID")
                text_elem = error_code_elem.find("TEXT")
                if id_elem is not None and text_elem is not None:
                    error_dict[id_elem.text] = text_elem.text
            
            # Convert error_code to string for lookup
            error_code_str = str(error_code)
            return error_dict.get(error_code_str, f"უცნობი შეცდომა: კოდი {error_code}")
            
        except Exception as e:
            _logger.exception("Error getting error codes from RS.GE")
            return f"შეცდომის კოდის მიღება ვერ მოხერხდა: {str(e)}"

    def _safe_soap_request(self, url, soap_body, headers, service_name="API"):
        """
        Send SOAP request with comprehensive error handling
        
        Args:
            url: SOAP endpoint URL
            soap_body: SOAP XML request body
            headers: HTTP headers
            service_name: Name of service for logging
            
        Returns:
            tuple: (success: bool, response_text: str, error_msg: str)
        """
        try:
            _logger.info(f'=== {service_name} REQUEST ===')
            _logger.info(f'URL: {url}')
            _logger.info(f'Body: {soap_body[:500]}...' if len(soap_body) > 500 else f'Body: {soap_body}')
            
            response = requests.post(
                url, 
                data=soap_body.encode('utf-8'), 
                headers=headers,
                timeout=60  # 60 second timeout
            )
            
            _logger.info(f'{service_name} Response Status: {response.status_code}')
            _logger.info(f'{service_name} Response: {response.text[:500]}...' if len(response.text) > 500 else f'{service_name} Response: {response.text}')
            
            # Check HTTP status
            if response.status_code != 200:
                error_msg = f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
                return False, response.text, error_msg
            
            # Check for SOAP faults
            if 'soap:Fault' in response.text or 'faultstring' in response.text:
                try:
                    root = ET.fromstring(response.text)
                    fault_string = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Body/{http://schemas.xmlsoap.org/soap/envelope/}Fault/faultstring')
                    if fault_string is not None:
                        error_msg = f"SOAP შეცდომა: {fault_string.text}"
                        return False, response.text, error_msg
                except:
                    pass
                error_msg = "SOAP შეცდომა დაფიქსირდა"
                return False, response.text, error_msg
            
            return True, response.text, None
            
        except requests.exceptions.Timeout:
            error_msg = f"{service_name}: დროის ლიმიტი ამოიწურა (60 წამი)"
            _logger.error(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = f"{service_name}: კავშირის შეცდომა - შეამოწმეთ ინტერნეტი"
            _logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"{service_name}: {str(e)}"
            _logger.exception(f"Unexpected error in {service_name}")
            return False, None, error_msg

    def _parse_xml_response(self, response_text, xpath, namespaces=None):
        """
        Safely parse XML and extract element
        
        Args:
            response_text: XML response string
            xpath: XPath to element
            namespaces: XML namespaces dict
            
        Returns:
            str: Element text or None
        """
        if namespaces is None:
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
        
        try:
            root = ET.fromstring(response_text)
            element = root.find(xpath, namespaces)
            return element.text if element is not None else None
        except Exception as e:
            _logger.error(f"XML parsing error: {str(e)}")
            return None
    
    # ============================================================================
    # END HELPER METHODS
    # ============================================================================

    def generate_goods_list_xml(self):
        goods_list_xml = "<GOODS_LIST>"

        for move in self.move_ids_without_package:
            product = move.product_id
            quantity = move.product_uom_qty
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)
            amount = move.total_price
            barcode = product.barcode
            if not barcode:  # Check if the barcode is empty
                raise UserError(_('დაამატეთ ბარკოდი პროდუქციაზე'))

            unit_id = move.unit_id  # Assuming this is the correct field for unit_id
            if not unit_id:  # Check if the unit_id is empty
                raise UserError(_('დამატეთ rs.ge-ს ერთეული პროდუქციაზე'))
            tax_id = move.tax_id.name if move.tax_id else ''  # Assuming tax_id is a field in stock.move
            vat_type = -1  # or any other default value
            price_unit = move.total_price / quantity
            unit_txt = move.unit_txt
            category_name = product.x_studio_catname.x_name# Assuming this is the correct field for unit_txt

            if tax_id == '18%':
                vat_type = 0
            elif tax_id =='0%':
                vat_type = 1
            else:
                raise UserError(_('დაბეგვრა უნდა იყოს ან 18 ან 0'))


            goods_xml = f"""
                <GOODS>
                    <ID>0</ID>
                    <W_NAME>{category_name} {product.name}</W_NAME>
                    <UNIT_ID>{unit_id}</UNIT_ID>
                    <UNIT_TXT>{unit_txt}</UNIT_TXT>
                    <QUANTITY>{quantity}</QUANTITY>
                    <PRICE>{price_unit}</PRICE>
                    <STATUS>1</STATUS>
                    <AMOUNT>{amount}</AMOUNT>
                    <BAR_CODE>{barcode}</BAR_CODE>
                    <A_ID>0</A_ID>
                    <VAT_TYPE>{vat_type}</VAT_TYPE>
                </GOODS>
            """
            goods_list_xml += goods_xml

        goods_list_xml += "</GOODS_LIST>"
        return goods_list_xml

    def get_name_from_tin(self, rs_acc, rs_pass, tin):
        """Get company name from TIN with comprehensive error handling"""
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
      <soap:Body>
        <get_name_from_tin xmlns="http://tempuri.org/">
          <su>{rs_acc}</su>
          <sp>{rs_pass}</sp>
          <tin>{tin}</tin>
        </get_name_from_tin>
      </soap:Body>
    </soap:Envelope>"""

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_name_from_tin"
        }

        # Use safe request handler  
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"get_name_from_tin(TIN:{tin})"
        )
        
        if not success:
            _logger.error(f"get_name_from_tin failed: {error_msg}")
            return f"შეცდომა: {error_msg}"
        
        # Parse response safely
        name = self._parse_xml_response(
            response_text,
            './/ns:get_name_from_tinResult',
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 
             'ns': 'http://tempuri.org/'}
        )
        
        if not name:
            # Try fallback extraction
            if '<get_name_from_tinResult>' in response_text:
                start_tag = "<get_name_from_tinResult>"
                end_tag = "</get_name_from_tinResult>"
                start_index = response_text.find(start_tag) + len(start_tag)
                end_index = response_text.find(end_tag)
                result = response_text[start_index:end_index].strip()
                
                # Check if it's a negative error code
                if result.startswith('-'):
                    error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
                    _logger.error(f"get_name_from_tin error: {error_text}")
                    return f"შეცდომა: {error_text}"
                
                return result if result else "უცნობი"
            
            _logger.error("get_name_from_tin: Response empty")
            return "უცნობი (ცარიელი პასუხი)"
        
        _logger.info(f'✅ Name from TIN {tin}: {name}')
        return name



    @api.model
    def send_soap_request(self):
        goods_list_xml = self.generate_goods_list_xml()
        _logger.info(f"Generated Goods List XML: {goods_list_xml}")

        start_location = self.start_location
        end_location = self.editable_end_location
        driver_id = self.driver_id
        driver_type = self.driver_type
        driver_name = self.driver_name
        transport_cost = self.transport_cost
        car_number = self.car_number
        transport_cost_payer = self.transport_cost_payer
        trans_id = self.trans_id
        comment = self.comment
        trans_txt = self.trans_txt
        now = datetime.now()
        begin_date = self.begin_date
        formatted_begin_date=self.formatted_begin_date
        buyer_name=self.partner_id
        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        completed_soap = self.completed_soap
        buyer_tin = self.partner_vat
        buyer_type = self.buyer_type
        delivery = self.delivery



        if self.picking_type_id.code == 'internal':
            delivery = '1'
            end_location = self.editable_end_location
            # For internal transfers, use company's TIN instead of partner's TIN
            buyer_tin = self.company_id.vat or self.env.user.company_id.vat

        if self.return_id:
            delivery = '5'







      #  if self.combined_invoice_id:
      #      raise UserError("ზედნადები უკვე ატვირთულია")


        for record in self:
            try:
                usn = record.rs_acc  # Use the rs_acc field of the record
                usp = record.rs_pass  # Use the rs_pass field of the record
                tin = record.driver_id


                soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                      <soap:Body>
                        <get_name_from_tin xmlns="http://tempuri.org/">
                          <su>{usn}</su>
                          <sp>{usp}</sp>
                          <tin>{tin}</tin>
                        </get_name_from_tin>
                      </soap:Body>
                    </soap:Envelope>"""

                # Define the URL and headers
                url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_name_from_tin"
                }

                # Send the request
                response = requests.post(url, data=soap_request, headers=headers)

                # Check for a successful response
                if response.status_code != 200:
                    record.company_review = f"Failed to get response from service. Status code: {response.status_code}"


                # Parse the XML response
                root = ET.fromstring(response.text)

                # Define the namespace (use the appropriate namespace for your SOAP response)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
                }

                # Find the `name` element in the response
                result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

                # Check if the element was found and assign its text to the company_review field
                self.driver_name=result_element.text
            except Exception as e:
                record.company_review = f"An error occurred: {str(e)}"




        # Define the URL and headers
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }

        usn = record.rs_acc  # Use the rs_acc field of the record
        usp = record.rs_pass  # Replace with actual password

        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <chek_service_user xmlns="http://tempuri.org/">
              <su>{rs_acc}</su>
              <sp>{rs_pass}</sp>
            </chek_service_user>
          </soap:Body>
        </soap:Envelope>"""

        # Send the request
        response = requests.post(url, data=soap_body, headers=headers)

        # _logger.info the response status code
        _logger.info(response.status_code)

        # Parse the XML response
        root = ET.fromstring(response.text)

        # Define the namespace (use the appropriate namespace for your SOAP response)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        # Find the `un_id` element in the response
        un_id_element = root.find('.//ns:un_id', namespaces)
        seller_un_id = un_id_element.text

        soap_request = f"""
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
            <soap:Body>
                <save_waybill xmlns="http://tempuri.org/">
                    <su>{rs_acc}</su>
                    <sp>{rs_pass}</sp>
                    <waybill>
                        <WAYBILL xmlns="">
                            {goods_list_xml}
                            <ID>0</ID>
                            <TYPE>{delivery}</TYPE>
                            <BUYER_TIN>{buyer_tin}</BUYER_TIN>
                            <CHEK_BUYER_TIN>{buyer_type}</CHEK_BUYER_TIN>
                            <BUYER_NAME></BUYER_NAME>
                            <START_ADDRESS>{start_location}</START_ADDRESS>
                            <END_ADDRESS>{end_location}</END_ADDRESS>
                            <DRIVER_TIN>{driver_id}</DRIVER_TIN>
                            <CHEK_DRIVER_TIN>{driver_type}</CHEK_DRIVER_TIN>
                            <DRIVER_NAME>ა.კ</DRIVER_NAME>
                            <TRANSPORT_COAST>{transport_cost}</TRANSPORT_COAST>
                            <RECEPTION_INFO></RECEPTION_INFO>
                            <RECEIVER_INFO></RECEIVER_INFO>
                            <DELIVERY_DATE></DELIVERY_DATE>
                            <STATUS>0</STATUS>
                            <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                            <PAR_ID>0</PAR_ID>
                            <CAR_NUMBER>{car_number}</CAR_NUMBER>
                            <BEGIN_DATE>{formatted_begin_date}</BEGIN_DATE>
                            <TRAN_COST_PAYER>{transport_cost_payer}</TRAN_COST_PAYER>
                            <TRANS_ID>{trans_id}</TRANS_ID>
                            <TRANS_TXT>{trans_txt}</TRANS_TXT>
                            <COMMENT>{comment}</COMMENT>
                            <TRANSPORTER_TIN></TRANSPORTER_TIN>
                        </WAYBILL>
                    </waybill>
                </save_waybill>
            </soap:Body>
        </soap:Envelope>
        """

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_waybill"
        }

        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers)
        response_text = response.text

        # Comprehensive logging for debugging
        _logger.info(f'=== SOAP REQUEST DETAILS ===')
        _logger.info(f'URL: {url}')
        _logger.info(f'Headers: {headers}')
        _logger.info(f'Request Status Code: {response.status_code}')
        _logger.info(f'Response Headers: {dict(response.headers)}')
        _logger.info(f'Full SOAP Response Text: {response_text}')
        _logger.info(f'Response Length: {len(response_text)} characters')
        
        # Check for common response patterns
        _logger.info(f'=== RESPONSE ANALYSIS ===')
        _logger.info(f'Contains <STATUS>: {"<STATUS>" in response_text}')
        _logger.info(f'Contains </STATUS>: {"</STATUS>" in response_text}')
        _logger.info(f'Contains <soap:Envelope>: {"<soap:Envelope>" in response_text}')
        _logger.info(f'Contains <soap:Fault>: {"<soap:Fault>" in response_text}')
        _logger.info(f'Contains <faultstring>: {"<faultstring>" in response_text}')
        _logger.info(f'Contains <detail>: {"<detail>" in response_text}')
        
        # Log first 500 characters for quick inspection
        _logger.info(f'First 500 characters: {response_text[:500]}')
        
        # Extract Status with proper error handling
        try:
            if '<STATUS>' in response_text and '</STATUS>' in response_text:
                Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
                _logger.info(f'✅ Successfully extracted STATUS: {Status}')
            else:
                _logger.error(f'❌ No STATUS found in response')
                _logger.error(f'Full response for analysis: {response_text}')
                
                # Try to find any XML elements that might contain status information
                import re
                status_patterns = [
                    r'<STATUS[^>]*>(.*?)</STATUS>',
                    r'<status[^>]*>(.*?)</status>',
                    r'<Status[^>]*>(.*?)</Status>',
                    r'<result[^>]*>(.*?)</result>',
                    r'<Result[^>]*>(.*?)</Result>',
                ]
                
                for pattern in status_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    if matches:
                        _logger.info(f'Found potential status matches with pattern {pattern}: {matches}')
                
                raise UserError(f'Invalid response from server: No STATUS found. Response: {response_text[:200]}...')
        except IndexError:
            _logger.error(f'❌ Error parsing STATUS from response')
            _logger.error(f'Full response: {response_text}')
            raise UserError(f'Error parsing server response')
        if Status >= '0':
            # Parse XML response properly like in your other methods
            try:
                root = ET.fromstring(response_text)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'tempuri': 'http://tempuri.org/'
                }
                
                # Extract invoice_id using XML parsing
                id_element = root.find('.//ID')
                invoice_id = id_element.text if id_element is not None else None
                _logger.info(f'✅ Extracted invoice_id: {invoice_id}')
                
                # Extract invoice_number using XML parsing
                waybill_element = root.find('.//WAYBILL_NUMBER')
                invoice_number = waybill_element.text if waybill_element is not None else invoice_id
                
                if waybill_element is not None:
                    _logger.info(f'✅ Extracted invoice_number: {invoice_number}')
                else:
                    _logger.info(f'⚠️ No WAYBILL_NUMBER found, using invoice_id as invoice_number: {invoice_number}')
                    
            except ET.ParseError as e:
                _logger.error(f'❌ XML parsing error: {e}')
                # Fallback to string parsing if XML parsing fails
                try:
                    invoice_id = response_text.split('<ID>')[1].split('</ID>')[0]
                    _logger.info(f'✅ Fallback: Extracted invoice_id: {invoice_id}')
                except IndexError:
                    invoice_id = None
                    _logger.error('❌ Failed to extract invoice_id from response')

                try:
                    invoice_number = response_text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]
                    _logger.info(f'✅ Fallback: Extracted invoice_number: {invoice_number}')
                except IndexError:
                    invoice_number = invoice_id
                    _logger.info(f'⚠️ Fallback: No WAYBILL_NUMBER found, using invoice_id as invoice_number: {invoice_number}')

            # Update current model fields
            self.invoice_id = invoice_id
            self.invoice_number = invoice_number
            self.completed_soap = '1'

            # Create or update CombinedInvoiceModel record
            combined_invoice = self.env['combined.invoice.model'].search([], limit=1)
            if combined_invoice:
                # Update existing record
                combined_invoice.write({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                })
                _logger.info(f'Updated existing combined_invoice record with ID: {invoice_id}')
            else:
                # Create new record if none exists
                combined_invoice = self.env['combined.invoice.model'].create({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                })
                _logger.info(f'Created new combined_invoice record with ID: {invoice_id}')

            # Link the combined_invoice to current model
            self.combined_invoice_id = combined_invoice.id
            _logger.info(f'Successfully updated database records for invoice_id: {invoice_id}')

        elif Status < '0':
            # Define the SOAP request XML with the provided <su> and <sp> values
            soap_request = f"""
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                    </get_error_codes>
                </soap:Body>
            </soap:Envelope>
            """

            # Define the headers
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_error_codes"
            }

            # Send the SOAP request
            response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx", data=soap_request, headers=headers)

            # Comprehensive logging for get_error_codes
            _logger.info(f'=== GET_ERROR_CODES REQUEST DETAILS ===')
            _logger.info(f'URL: http://services.rs.ge/waybillservice/waybillservice.asmx')
            _logger.info(f'Headers: {headers}')
            _logger.info(f'Request Status Code: {response.status_code}')
            _logger.info(f'Response Headers: {dict(response.headers)}')
            _logger.info(f'Full SOAP Response Text: {response.text}')
            _logger.info(f'Response Length: {len(response.text)} characters')

            if response.status_code == 200:
                # Parse the XML response
                root = ET.fromstring(response.content)

                # Define the namespaces
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'tempuri': 'http://tempuri.org/'
                }

                # Initialize an empty dictionary to store ID and TEXT values
                error_dict = {}

                # Find all ERROR_CODE elements and extract ID and TEXT values
                for error_code in root.findall(".//ERROR_CODE"):
                    id_value = error_code.find("ID").text
                    text_value = error_code.find("TEXT").text
                    error_dict[id_value] = text_value

                # Compare Status to numbers in error_dict and get corresponding error text
                error_text = error_dict.get(Status, "No error found for this status")
                raise UserError(error_text)


    @api.model
    def _button_refresh_page(self):
        """Refresh the current form view."""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def button_send_soap_request(self):
        """Upload waybills - auto-detects single vs batch mode"""
        _logger.info(f'Executing button_send_soap_request for {len(self)} record(s)')
        
        # Single record mode - original behavior with page refresh
        if len(self) == 1:
            for record in self:
                if not record.invoice_id:
                    record.send_soap_request()
                    
                    # Refresh the page
                    self.env.cr.commit()
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                        'params': {
                            'next': {
                                'type': 'ir.actions.client',
                                'tag': 'display_notification',
                                'params': {
                                    'title': _('Success'),
                                    'message': _('ზედნადები წარმატებით აიტვირთა'),
                                    'type': 'success',
                                    'sticky': False,
                                }
                            }
                        }
                    }
                else:
                    raise UserError(_('ზედნადები უკვე ატვირთლია'))
        
        # Batch mode - process all records with error handling
        else:
            success_records = []
            error_records = []
            skipped_records = []
            
            for record in self:
                try:
                    if record.invoice_id:
                        skipped_records.append((record.name, 'ზედნადები უკვე ატვირთულია'))
                        continue
                        
                    record.send_soap_request()
                    success_records.append(record.name)
                    self.env.cr.commit()  # Commit after each successful record
                    
                except Exception as e:
                    error_records.append((record.name, str(e)))
                    self.env.cr.rollback()  # Rollback failed record
                    _logger.exception(f"Error processing delivery {record.name}")
            
            # Build result message
            messages = []
            if success_records:
                messages.append(f"✓ წარმატებით ატვირთულია ({len(success_records)}): {', '.join(success_records)}")
            if skipped_records:
                skipped_msg = '\n'.join([f"  - {name}: {reason}" for name, reason in skipped_records])
                messages.append(f"⊘ გამოტოვებულია ({len(skipped_records)}):\n{skipped_msg}")
            if error_records:
                error_msg = '\n'.join([f"  - {name}: {error}" for name, error in error_records])
                messages.append(f"✗ შეცდომები ({len(error_records)}):\n{error_msg}")
            
            final_message = '\n\n'.join(messages)
            
            if error_records and not success_records:
                raise UserError(final_message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ზედნადებების ატვირთვა დასრულდა'),
                    'message': final_message,
                    'type': 'success' if not error_records else 'warning',
                    'sticky': True,
                }
            }


    @api.model
    def send_soap_request_return(self):
        goods_list_xml = "<GOODS_LIST>"

        for move in self.move_ids_without_package:
            product = move.product_id
            quantity = move.product_uom_qty
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product.name)
            amount = move.cost_including_tax
            barcode = product.barcode
            unit_id = move.unit_id  # Assuming this is the correct field for unit_id
            tax_id = move.tax_id.name if move.tax_id else ''  # Assuming tax_id is a field in stock.move
            vat_type = -1  # or any other default value
            price_unit = amount / quantity
            unit_txt = move.unit_txt  # Assuming this is the correct field for unit_txt

            if tax_id == '18':
                vat_type = 0
            elif tax_id =='0':
                vat_type = 1

            goods_xml = f"""
                <GOODS>
                    <ID>0</ID>
                    <W_NAME>{product.x_studio_catname.x_name}{product.name}</W_NAME>
                    <UNIT_ID>{unit_id}</UNIT_ID>
                    <UNIT_TXT>{unit_txt}</UNIT_TXT>
                    <QUANTITY>{quantity}</QUANTITY>
                    <PRICE>{price_unit}</PRICE>
                    <STATUS>1</STATUS>
                    <AMOUNT>{amount}</AMOUNT>
                    <BAR_CODE>{barcode}</BAR_CODE>
                    <A_ID>0</A_ID>
                    <VAT_TYPE>{vat_type}</VAT_TYPE>
                </GOODS>
            """
            goods_list_xml += goods_xml

        goods_list_xml += "</GOODS_LIST>"
        start_location = self.start_location
        end_location = self.editable_end_location
        driver_id = self.driver_id
        driver_type = self.driver_type
        driver_name = self.driver_name
        transport_cost = self.transport_cost
        car_number = self.car_number
        transport_cost_payer = self.transport_cost_payer
        trans_id = self.trans_id
        comment = self.comment
        trans_txt = self.trans_txt
        now = datetime.now()
        begin_date = self.begin_date
        formatted_begin_date=self.formatted_begin_date
        buyer_name=self.partner_id
        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        completed_soap = self.completed_soap
        buyer_tin = self.partner_vat
        field5 = self.field5
        if self.combined_invoice_id:
            raise UserError("ზედნადები უკვე ატვირთულია")

        for record in self:
            try:
                usn = record.rs_acc  # Use the rs_acc field of the record
                usp = record.rs_pass  # Use the rs_pass field of the record
                tin = record.driver_id


                soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
                    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                      <soap:Body>
                        <get_name_from_tin xmlns="http://tempuri.org/">
                          <su>{usn}</su>
                          <sp>{usp}</sp>
                          <tin>{tin}</tin>
                        </get_name_from_tin>
                      </soap:Body>
                    </soap:Envelope>"""

                # Define the URL and headers
                url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_name_from_tin"
                }

                # Send the request
                response = requests.post(url, data=soap_request, headers=headers)

                # Check for a successful response
                if response.status_code != 200:
                    record.company_review = f"Failed to get response from service. Status code: {response.status_code}"


                # Parse the XML response
                root = ET.fromstring(response.text)

                # Define the namespace (use the appropriate namespace for your SOAP response)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
                }

                # Find the `name` element in the response
                result_element = root.find('.//ns:get_name_from_tinResult', namespaces)

                # Check if the element was found and assign its text to the company_review field
                self.driver_name=result_element.text
            except Exception as e:
                record.company_review = f"An error occurred: {str(e)}"






        # Define the URL and headers
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
        }


        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <chek_service_user xmlns="http://tempuri.org/">
                      <su>{rs_acc}/su>
                  <sp>{rs_pass}</sp>
                </chek_service_user>
              </soap:Body>
            </soap:Envelope>"""

        # Send the request
        response = requests.post(url, data=soap_body, headers=headers)

        # _logger.info the response status code
        _logger.info(response.status_code)

        # Parse the XML response
        root = ET.fromstring(response.text)

        # Define the namespace (use the appropriate namespace for your SOAP response)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        # Find the `un_id` element in the response
        un_id_element = root.find('.//ns:un_id', namespaces)
        seller_un_id = un_id_element.text


        soap_request = f"""
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    <save_waybill xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                        <waybill>
                            <WAYBILL xmlns="">
                                {goods_list_xml}
                                <ID>0</ID>
                                <TYPE>{field5}</TYPE>
                                <BUYER_TIN>{buyer_tin}</BUYER_TIN>
                                <CHEK_BUYER_TIN></CHEK_BUYER_TIN>
                                <BUYER_NAME></BUYER_NAME>
                                <START_ADDRESS>{start_location}</START_ADDRESS>
                                <END_ADDRESS>{end_location}</END_ADDRESS>
                                <DRIVER_TIN>{driver_id}</DRIVER_TIN>
                                <CHEK_DRIVER_TIN>{driver_type}</CHEK_DRIVER_TIN>
                                <DRIVER_NAME>{driver_name}</DRIVER_NAME>
                                <TRANSPORT_COAST>{transport_cost}</TRANSPORT_COAST>
                                <RECEPTION_INFO></RECEPTION_INFO>
                                <RECEIVER_INFO></RECEIVER_INFO>
                                <DELIVERY_DATE></DELIVERY_DATE>
                                <STATUS>1</STATUS>
                                <SELER_UN_ID>{seller_un_id}</SELER_UN_ID>
                                <PAR_ID>0</PAR_ID>
                                <CAR_NUMBER>{car_number}</CAR_NUMBER>
                                <BEGIN_DATE>{formatted_begin_date}</BEGIN_DATE>
                                <TRAN_COST_PAYER>{transport_cost_payer}</TRAN_COST_PAYER>
                                <TRANS_ID>{trans_id}</TRANS_ID>
                                <TRANS_TXT>{trans_txt}</TRANS_TXT>
                                <COMMENT>{comment}</COMMENT>
                                <TRANSPORTER_TIN></TRANSPORTER_TIN>
                            </WAYBILL>
                        </waybill>
                    </save_waybill>
                </soap:Body>
            </soap:Envelope>
            """

        url = "http://services.rs.ge/waybillservice/waybillservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_waybill"
        }
        _logger.info(soap_request.encode('utf-8'))

        response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers)
        response_text = response.text

        # Comprehensive logging for debugging
        _logger.info(f'=== SOAP REQUEST DETAILS ===')
        _logger.info(f'URL: {url}')
        _logger.info(f'Headers: {headers}')
        _logger.info(f'Request Status Code: {response.status_code}')
        _logger.info(f'Response Headers: {dict(response.headers)}')
        _logger.info(f'Full SOAP Response Text: {response_text}')
        _logger.info(f'Response Length: {len(response_text)} characters')
        
        # Check for common response patterns
        _logger.info(f'=== RESPONSE ANALYSIS ===')
        _logger.info(f'Contains <STATUS>: {"<STATUS>" in response_text}')
        _logger.info(f'Contains </STATUS>: {"</STATUS>" in response_text}')
        _logger.info(f'Contains <soap:Envelope>: {"<soap:Envelope>" in response_text}')
        _logger.info(f'Contains <soap:Fault>: {"<soap:Fault>" in response_text}')
        _logger.info(f'Contains <faultstring>: {"<faultstring>" in response_text}')
        _logger.info(f'Contains <detail>: {"<detail>" in response_text}')
        
        # Log first 500 characters for quick inspection
        _logger.info(f'First 500 characters: {response_text[:500]}')
        
        # Extract Status with proper error handling
        try:
            if '<STATUS>' in response_text and '</STATUS>' in response_text:
                Status = response_text.split('<STATUS>')[1].split('</STATUS>')[0]
                _logger.info(f'✅ Successfully extracted STATUS: {Status}')
            else:
                _logger.error(f'❌ No STATUS found in response')
                _logger.error(f'Full response for analysis: {response_text}')
                
                # Try to find any XML elements that might contain status information
                import re
                status_patterns = [
                    r'<STATUS[^>]*>(.*?)</STATUS>',
                    r'<status[^>]*>(.*?)</status>',
                    r'<Status[^>]*>(.*?)</Status>',
                    r'<result[^>]*>(.*?)</result>',
                    r'<Result[^>]*>(.*?)</Result>',
                ]
                
                for pattern in status_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    if matches:
                        _logger.info(f'Found potential status matches with pattern {pattern}: {matches}')
                
                raise UserError(f'Invalid response from server: No STATUS found. Response: {response_text[:200]}...')
        except IndexError:
            _logger.error(f'❌ Error parsing STATUS from response')
            _logger.error(f'Full response: {response_text}')
            raise UserError(f'Error parsing server response')
        if Status >= '0':
            # Parse XML response properly like in your other methods
            try:
                root = ET.fromstring(response_text)
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'tempuri': 'http://tempuri.org/'
                }
                
                # Extract invoice_id using XML parsing
                id_element = root.find('.//ID')
                invoice_id = id_element.text if id_element is not None else None
                _logger.info(f'✅ Extracted invoice_id: {invoice_id}')
                
                # Extract invoice_number using XML parsing
                waybill_element = root.find('.//WAYBILL_NUMBER')
                invoice_number = waybill_element.text if waybill_element is not None else invoice_id
                
                if waybill_element is not None:
                    _logger.info(f'✅ Extracted invoice_number: {invoice_number}')
                else:
                    _logger.info(f'⚠️ No WAYBILL_NUMBER found, using invoice_id as invoice_number: {invoice_number}')
                    
            except ET.ParseError as e:
                _logger.error(f'❌ XML parsing error: {e}')
                # Fallback to string parsing if XML parsing fails
                try:
                    invoice_id = response_text.split('<ID>')[1].split('</ID>')[0]
                    _logger.info(f'✅ Fallback: Extracted invoice_id: {invoice_id}')
                except IndexError:
                    invoice_id = None
                    _logger.error('❌ Failed to extract invoice_id from response')

                try:
                    invoice_number = response_text.split('<WAYBILL_NUMBER>')[1].split('</WAYBILL_NUMBER>')[0]
                    _logger.info(f'✅ Fallback: Extracted invoice_number: {invoice_number}')
                except IndexError:
                    invoice_number = invoice_id
                    _logger.info(f'⚠️ Fallback: No WAYBILL_NUMBER found, using invoice_id as invoice_number: {invoice_number}')

            # Update current model fields
            self.invoice_id = invoice_id
            self.invoice_number = invoice_number
            self.completed_soap = '1'

            # Create or update CombinedInvoiceModel record
            combined_invoice = self.env['combined.invoice.model'].search([], limit=1)
            if combined_invoice:
                # Update existing record
                combined_invoice.write({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                })
                _logger.info(f'Updated existing combined_invoice record with ID: {invoice_id}')
            else:
                # Create new record if none exists
                combined_invoice = self.env['combined.invoice.model'].create({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                })
                _logger.info(f'Created new combined_invoice record with ID: {invoice_id}')

            # Link the combined_invoice to current model
            self.combined_invoice_id = combined_invoice.id
            _logger.info(f'Successfully updated database records for invoice_id: {invoice_id}')

        elif Status < '0':
            # Define the SOAP request XML with the provided <su> and <sp> values
            soap_request = f"""
                    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                        <soap:Body>
                            <get_error_codes xmlns="http://tempuri.org/">
                                <su>{rs_acc}</su>
                                <sp>{rs_pass}</sp>
                            </get_error_codes>
                        </soap:Body>
                    </soap:Envelope>
                    """

            # Define the headers
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_error_codes"
            }

            # Send the SOAP request
            response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx", data=soap_request, headers=headers)

            # Comprehensive logging for get_error_codes
            _logger.info(f'=== GET_ERROR_CODES REQUEST DETAILS ===')
            _logger.info(f'URL: http://services.rs.ge/waybillservice/waybillservice.asmx')
            _logger.info(f'Headers: {headers}')
            _logger.info(f'Request Status Code: {response.status_code}')
            _logger.info(f'Response Headers: {dict(response.headers)}')
            _logger.info(f'Full SOAP Response Text: {response.text}')
            _logger.info(f'Response Length: {len(response.text)} characters')

            if response.status_code == 200:
                # Parse the XML response
                root = ET.fromstring(response.content)

                # Define the namespaces
                namespaces = {
                    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                    'tempuri': 'http://tempuri.org/'
                }

                # Initialize an empty dictionary to store ID and TEXT values
                error_dict = {}

                # Find all ERROR_CODE elements and extract ID and TEXT values
                for error_code in root.findall(".//ERROR_CODE"):
                    id_value = error_code.find("ID").text
                    text_value = error_code.find("TEXT").text
                    error_dict[id_value] = text_value

                # Compare Status to numbers in error_dict and get corresponding error text
                error_text = error_dict.get(Status, "No error found for this status")
                raise UserError(error_text)



    def button_send_soap_request_return(self):
        _logger.info('Executing button_send_soap_request_return method')
        for record in self:
            if not record.invoice_id:  # Check if invoice_id is empty
                record.send_soap_request_return()
            else:
                raise UserError('ზედნადები უკვე ატვირთლია')

from datetime import timezone, timedelta, datetime



#add _logger.infos for testing purposes
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # ============================================================================
    # HELPER METHODS FOR ERROR HANDLING
    # ============================================================================
    
    def _get_error_text_from_code(self, rs_acc, rs_pass, error_code):
        """
        Get human-readable error text from RS.GE error code
        
        Args:
            rs_acc: RS account username
            rs_pass: RS account password  
            error_code: Error code (negative number or string)
            
        Returns:
            str: Error message in Georgian
        """
        try:
            soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" 
                           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                    </get_error_codes>
                </soap:Body>
            </soap:Envelope>
            """
            
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_error_codes"
            }
            
            response = requests.post(
                "http://services.rs.ge/waybillservice/waybillservice.asmx",
                data=soap_request,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                return f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
            
            root = ET.fromstring(response.content)
            error_dict = {}
            
            for error_code_elem in root.findall(".//ERROR_CODE"):
                id_elem = error_code_elem.find("ID")
                text_elem = error_code_elem.find("TEXT")
                if id_elem is not None and text_elem is not None:
                    error_dict[id_elem.text] = text_elem.text
            
            # Convert error_code to string for lookup
            error_code_str = str(error_code)
            return error_dict.get(error_code_str, f"უცნობი შეცდომა: კოდი {error_code}")
            
        except Exception as e:
            _logger.exception("Error getting error codes from RS.GE")
            return f"შეცდომის კოდის მიღება ვერ მოხერხდა: {str(e)}"

    def _safe_soap_request(self, url, soap_body, headers, service_name="API"):
        """
        Send SOAP request with comprehensive error handling
        
        Args:
            url: SOAP endpoint URL
            soap_body: SOAP XML request body
            headers: HTTP headers
            service_name: Name of service for logging
            
        Returns:
            tuple: (success: bool, response_text: str, error_msg: str)
        """
        try:
            _logger.info(f'=== {service_name} REQUEST ===')
            _logger.info(f'URL: {url}')
            _logger.info(f'Body: {soap_body[:500]}...' if len(soap_body) > 500 else f'Body: {soap_body}')
            
            response = requests.post(
                url, 
                data=soap_body.encode('utf-8'), 
                headers=headers,
                timeout=60  # 60 second timeout
            )
            
            _logger.info(f'{service_name} Response Status: {response.status_code}')
            _logger.info(f'{service_name} Response: {response.text[:500]}...' if len(response.text) > 500 else f'{service_name} Response: {response.text}')
            
            # Check HTTP status
            if response.status_code != 200:
                error_msg = f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
                return False, response.text, error_msg
            
            # Check for SOAP faults
            if 'soap:Fault' in response.text or 'faultstring' in response.text:
                try:
                    root = ET.fromstring(response.text)
                    fault_string = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Body/{http://schemas.xmlsoap.org/soap/envelope/}Fault/faultstring')
                    if fault_string is not None:
                        error_msg = f"SOAP შეცდომა: {fault_string.text}"
                        return False, response.text, error_msg
                except:
                    pass
                error_msg = "SOAP შეცდომა დაფიქსირდა"
                return False, response.text, error_msg
            
            return True, response.text, None
            
        except requests.exceptions.Timeout:
            error_msg = f"{service_name}: დროის ლიმიტი ამოიწურა (60 წამი)"
            _logger.error(error_msg)
            return False, None, error_msg
            
        except requests.exceptions.ConnectionError:
            error_msg = f"{service_name}: კავშირის შეცდომა - შეამოწმეთ ინტერნეტი"
            _logger.error(error_msg)
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"{service_name}: {str(e)}"
            _logger.exception(f"Unexpected error in {service_name}")
            return False, None, error_msg

    def _parse_xml_response(self, response_text, xpath, namespaces=None):
        """
        Safely parse XML and extract element
        
        Args:
            response_text: XML response string
            xpath: XPath to element
            namespaces: XML namespaces dict
            
        Returns:
            str: Element text or None
        """
        if namespaces is None:
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
        
        try:
            root = ET.fromstring(response_text)
            element = root.find(xpath, namespaces)
            return element.text if element is not None else None
        except Exception as e:
            _logger.error(f"XML parsing error: {str(e)}")
            return None
    
    # ============================================================================
    # END HELPER METHODS
    # ============================================================================
    
    def get_invoice(self, factura_num, rs_acc, rs_pass):
        """Get invoice details with comprehensive error handling"""
        
        user_id = self.chek(rs_acc, rs_pass)
        
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
                <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                  <soap12:Body>
                    <get_invoice xmlns="http://tempuri.org/">
                      <user_id>{user_id}</user_id>
                      <invois_id>{factura_num}</invois_id>
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                    </get_invoice>
                  </soap12:Body>
                </soap12:Envelope>'''

        headers = {
            'Content-Type': 'application/soap+xml; charset=utf-8',
            'Content-Length': str(len(soap_request)),
        }

        url = 'http://www.revenue.mof.ge/ntosservice/ntosservice.asmx'
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"get_invoice({factura_num})"
        )
        
        if not success:
            raise UserError(f"ფაქტურის მონაცემების მიღება ვერ მოხერხდა: {error_msg}")

        # Extract the specific elements
        ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'tempuri': 'http://tempuri.org/'}
        
        f_series = self._parse_xml_response(response_text, './/tempuri:f_series', ns)
        f_number = self._parse_xml_response(response_text, './/tempuri:f_number', ns)

        f_series_value = f_series if f_series else ''
        f_number_value = f_number if f_number else ''
        f_complete = f"{f_series_value} {f_number_value}".strip()
        
        if not f_complete:
            raise UserError(f"ფაქტურის ნომერი ვერ მოიძებნა: {factura_num}")
        
        _logger.info(f'✅ Invoice retrieved: {f_complete} for factura_num: {factura_num}')
        return f_complete




    def check_seller_and_service_user_id(self, rs_acc, rs_pass):
        """Check service user with comprehensive error handling"""
        
        _logger.info('Starting check_seller_and_service_user_id')
        
        # First check - RS.GE service
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <chek_service_user xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                    </chek_service_user>
                  </soap:Body>
                </soap:Envelope>"""
        
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_body, headers, "chek_service_user"
        )
        
        if not success:
            raise UserError(f"RS.GE ავტორიზაცია ვერ მოხერხდა: {error_msg}")
        
        # Parse un_id
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        seller_un_id = self._parse_xml_response(response_text, './/ns:un_id', namespaces)
        
        if not seller_un_id:
            # Check for error code in response
            error_code = self._parse_xml_response(response_text, './/ns:error', namespaces)
            if error_code:
                error_text = self._get_error_text_from_code(rs_acc, rs_pass, error_code)
                raise UserError(f"RS.GE ავტორიზაცია ვერ მოხერხდა: {error_text}")
            raise UserError("un_id ვერ მოიძებნა RS.GE პასუხში")
        
        _logger.info(f'Seller UN ID: {seller_un_id}')
        
        # Second check - Revenue service
        url = "https://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                  <soap12:Body>
                    <chek xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                      <user_id>{seller_un_id}</user_id>
                    </chek>
                  </soap12:Body>
                </soap12:Envelope>"""
        
        headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_body, headers, "chek(Revenue)"
        )
        
        if not success:
            raise UserError(f"Revenue სერვისი: ავტორიზაცია ვერ მოხერხდა: {error_msg}")
        
        user_id = self._parse_xml_response(response_text, './/ns:user_id', namespaces)
        
        if not user_id:
            raise UserError("user_id ვერ მოიძებნა Revenue სერვისის პასუხში")
        
        _logger.info(f'✅ Seller UN ID: {seller_un_id}, User ID: {user_id}')
        return seller_un_id, user_id

    def rs_un_id(self, rs_acc, rs_pass):
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
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }

        un_id_element = root.find('.//ns:un_id', namespaces)
        un_id = un_id_element.text if un_id_element is not None else None

        s_user_element = root.find('.//ns:s_user_id', namespaces)
        s_user_id = s_user_element.text if s_user_element is not None else None
        (_logger.info(un_id, s_user_id))

        return un_id, s_user_id

    def chek(self, rs_acc, rs_pass):
        """Check Revenue service user with comprehensive error handling"""
        
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

        success, response_text, error_msg = self._safe_soap_request(
            url, body, headers, "chek(Revenue)"
        )
        
        if not success:
            raise UserError(f"Revenue ავტორიზაცია ვერ მოხერხდა: {error_msg}")

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }

        user_id = self._parse_xml_response(response_text, './/ns:user_id', namespaces)
        
        if not user_id:
            raise UserError("user_id ვერ მოიძებნა Revenue პასუხში")
        
        _logger.info(f'✅ Revenue User ID: {user_id}')
        return user_id

    def un_id_from_tin(self, rs_acc, rs_pass, tin):
        """Get UN ID from TIN with comprehensive error handling"""
        
        user_id = self.chek(rs_acc, rs_pass)

        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_un_id_from_tin"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_un_id_from_tin xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <tin>{tin}</tin>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </get_un_id_from_tin>
              </soap:Body>
            </soap:Envelope>
            """

        success, response_text, error_msg = self._safe_soap_request(
            url, body, headers, f"get_un_id_from_tin(TIN:{tin})"
        )
        
        if not success:
            raise UserError(f"UN ID-ს მიღება ვერ მოხერხდა: {error_msg}")

        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }

        un_id = self._parse_xml_response(response_text, './/ns:get_un_id_from_tinResult', namespaces)
        saxeli = self._parse_xml_response(response_text, './/ns:name', namespaces)
        
        if not un_id:
            raise UserError(f"UN ID ვერ მოიძებნა TIN-ისთვის: {tin}")
        
        _logger.info(f'✅ UN ID from TIN {tin}: {un_id}, Name: {saxeli}')
        return un_id

    def save_invoice_momsaxureba(self, rs_acc, rs_pass, tin):
        user_id = self.chek(rs_acc, rs_pass)
        un_id, s_user_id = self.rs_un_id(rs_acc, rs_pass)
        buyer_un_id = self.un_id_from_tin(rs_acc, rs_pass, tin)
        
        # Use document's date fields instead of current system time
        if self.invoice_date:
            # Use invoice_date if available
            doc_date = self.invoice_date
        elif self.date:
            # Fallback to accounting date
            doc_date = self.date
        else:
            # Last resort: use current time
            doc_date = fields.Date.today()
        
        # Convert to datetime with timezone for SOAP request
        if isinstance(doc_date, str):
            doc_date = fields.Date.from_string(doc_date)
        
        # Create datetime object with time component (default to 12:00:00)
        doc_datetime = datetime.combine(doc_date, datetime.min.time().replace(hour=12))
        tz = timezone(timedelta(hours=4))
        doc_datetime_tz = doc_datetime.replace(tzinfo=tz)
        formatted_datetime = doc_datetime_tz.strftime('%Y-%m-%dT%H:%M:%S%z')
        formatted_datetime = f"{formatted_datetime[:-2]}:{formatted_datetime[-2:]}"  # Format as +04:00


        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_invoice"
        }
        body = f"""<?xml version="1.0" encoding="utf-8"?>
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <save_invoice xmlns="http://tempuri.org/">
                      <user_id>{user_id}</user_id>
                      <invois_id>0</invois_id>
                      <operation_date>{formatted_datetime}</operation_date>
                      <seller_un_id>{un_id}</seller_un_id>
                      <buyer_un_id>{buyer_un_id}</buyer_un_id>
                      <overhead_no>A</overhead_no>
                      <overhead_dt>{formatted_datetime}</overhead_dt>
                      <b_s_user_id>0</b_s_user_id>
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                    </save_invoice>
                  </soap:Body>
                </soap:Envelope>"""

        response = requests.post(url, data=body, headers=headers)
        root = ET.fromstring(response.text)
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
        }
        factura_num = root.find('.//ns:invois_id', namespaces)
        factura_num = factura_num.text if factura_num is not None else None
        _logger.info('Saved invoice with factura_num:', factura_num)
        return factura_num

    def save_invoice_desc_momsaxureba(self, rs_acc, rs_pass,factura_num):
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/save_invoice_desc"
        }
        user_id = self.chek(rs_acc, rs_pass)

        _logger.info('Generating goods list XML and sending SOAP requests')
        # Define the unit_id dictionary
        unit_id_dict = {
            '1': 'ცალი',
            '2': 'კგ',
            '3': 'გრამი',
            '4': 'ლიტრი',
            '5': 'ტონა',
            '7': 'სანტიმეტრი',
            '8': 'მეტრი',
            '9': 'კილომეტრი',
            '10': 'კვ.სმ',
            '11': 'კვ.მ',
            '12': 'მ³',
            '13': 'მილილიტრი',
            '99': 'სხვა'
        }

        for index, line in enumerate(self.invoice_line_ids):
            product = line.name
            unit_txt = line.unit_txt
            quantity = line.quantity
            if quantity == 0:
                raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % product)
            price_unit = line.price_unit
            amount = line.price_total
            tax_id = line.tax_ids.name

            # Check if unit_id exists in the dictionary; if not, default to 'მომსახურება'
            unit_id = unit_id_dict.get(line.unit_id, 'მომსახურება')

            body = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <save_invoice_desc xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <id>0</id>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                  <invois_id>{factura_num}</invois_id>
                  <goods>{product}</goods>
                  <g_unit>{unit_id}</g_unit>
                  <g_number>{quantity}</g_number>
                  <full_amount>{amount}</full_amount>
                  <drg_amount>18</drg_amount>
                  <aqcizi_amount>0</aqcizi_amount>
                  <akciz_id>0</akciz_id>
                </save_invoice_desc>
              </soap:Body>
            </soap:Envelope>"""


            _logger.info(factura_num)
            _logger.info(body)

            # Send SOAP request
            response = requests.post(url, headers=headers, data=body.encode('utf-8'))
            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'  # Adjust this namespace if it differs
            }
            save_invoice_desc_id = root.find('.//ns:id', namespaces)
            if save_invoice_desc_id is not None:
                save_invoice_desc_id = save_invoice_desc_id.text
                _logger.info(f'Saved invoice description for product {index} with ID:', save_invoice_desc_id)
                _logger.info(save_invoice_desc_id)
            else:
                _logger.info(f'Failed to save invoice description for product {index}')

        return True  # Or handle success/failure as needed
    def change_status_invoice(self, rs_pass, rs_acc, factura_num):
        """Change invoice status with comprehensive error handling"""
        
        seller_un_id, user_id = self.check_seller_and_service_user_id(rs_acc, rs_pass)

        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <change_invoice_status xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <inv_id>{factura_num}</inv_id>
                  <status>1</status>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </change_invoice_status>
              </soap:Body>
            </soap:Envelope>'''

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'Content-Length': str(len(soap_request)),
            'SOAPAction': '"http://tempuri.org/change_invoice_status"'
        }

        url = 'http://www.revenue.mof.ge/ntosservice/ntosservice.asmx'
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"change_invoice_status({factura_num})"
        )
        
        if not success:
            raise UserError(f"ფაქტურის სტატუსის შეცვლა ვერ მოხერხდა: {error_msg}")
        
        # Check for error in response
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        # Try to find result/error code
        result = self._parse_xml_response(response_text, './/ns:change_invoice_statusResult', namespaces)
        
        if result and result.startswith('-'):
            # Error code returned
            raise UserError(f"ფაქტურის სტატუსის შეცვლა ვერ მოხერხდა: კოდი {result}")
        
        _logger.info(f'✅ Invoice status changed successfully for: {factura_num}')
        return True

    def generate_goods_list_xml_1(self, line):
        """Generate XML for a single line item, skipping lines with unit_id or product_id"""
        # Skip if line has unit_id or product_id
        if line.unit_id or line.product_id:
            _logger.info(f'Skipping line with unit_id or product_id: {line.name}')
            return None

        if not line.name:
            return None

        quantity = line.quantity
        if quantity == 0:
            raise UserError("რაოდენობა ვერ იქნება ნულის ტოლი product: %s" % (line.product_id.name if line.product_id else line.name))

        price_unit = line.price_unit
        amount = quantity * price_unit

        momsaxureba_xml = f"""
            <goods>{line.name}</goods>
            <g_unit>მომსახურება</g_unit>
            <g_number>{quantity}</g_number>
            <full_amount>{amount}</full_amount>
            <drg_amount>18</drg_amount>
            <aqcizi_amount>0</aqcizi_amount>
            <akciz_id>0</akciz_id>
        """

        _logger.info(f'Generated XML for line item: {line.name}')
        return momsaxureba_xml
    def _get_error_text(self, rs_acc, rs_pass, error_code):
        """Helper method to get error text from error code"""
        soap_request = f"""
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
                <soap:Body>
                    <get_error_codes xmlns="http://tempuri.org/">
                        <su>{rs_acc}</su>
                        <sp>{rs_pass}</sp>
                    </get_error_codes>
                </soap:Body>
            </soap:Envelope>
        """

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_error_codes"
        }

        response = requests.post("http://services.rs.ge/waybillservice/waybillservice.asmx",
                                 data=soap_request,
                                 headers=headers)

        if response.status_code != 200:
            return f"Error getting error codes: {response.status_code}"

        root = ET.fromstring(response.content)
        error_dict = {}

        for error_code_elem in root.findall(".//ERROR_CODE"):
            id_value = error_code_elem.find("ID").text
            text_value = error_code_elem.find("TEXT").text
            error_dict[id_value] = text_value

        return error_dict.get(str(error_code), "Unknown error")

    def faqturebi(self):
        _logger.info('Executing faqturebi method')

        buyer_tin = self.partner_id.vat
        rs_acc = self.rs_acc
        rs_pass = self.rs_pass
        invoice_id = self.invoice_id

        if invoice_id:


            # Get user_id first
            user_id = self.chek(rs_acc, rs_pass)

            # First SOAP call to save_invoice
            soap_request = f"""
                <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                  <soap:Body>
                    <save_invoice xmlns="http://tempuri.org/">
                      <su>{rs_acc}</su>
                      <sp>{rs_pass}</sp>
                      <waybill_id>{invoice_id}</waybill_id>
                      <in_inv_id>0</in_inv_id>
                    </save_invoice>
                  </soap:Body>
                </soap:Envelope>
            """

            url = 'http://services.rs.ge/WayBillService/WayBillService.asmx'
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://tempuri.org/save_invoice',
            }

            response = requests.post(url, data=soap_request, headers=headers)
            _logger.info('SOAP Request to save invoice:', response.text)

            root = ET.fromstring(response.text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'tempuri': 'http://tempuri.org/'
            }

            out_inv_id_element = root.find('.//tempuri:out_inv_id', namespaces)
            if out_inv_id_element is None:
                raise UserError("Unable to find 'out_inv_id' in the response")

            out_inv_id = out_inv_id_element.text
            _logger.info(f'Got out_inv_id: {out_inv_id}')

            save_invoiceResult = int(root.find('.//tempuri:save_invoiceResult', namespaces).text)

            # Handle error codes if needed
            if save_invoiceResult < 0:
                error_text = self._get_error_text(rs_acc, rs_pass, save_invoiceResult)
                _logger.error(f'Error saving invoice: {error_text}')
                raise UserError(error_text)

            # Process each line item separately
            for line in self.invoice_line_ids:
                momsaxureba_xml = self.generate_goods_list_xml_1(line)
                if not momsaxureba_xml:
                    continue

                # Send individual SOAP request for each line
                soap_request = f"""
                    <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
                                  xmlns:xsd="http://www.w3.org/2001/XMLSchema" 
                                  xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                      <soap:Body>
                        <save_invoice_desc xmlns="http://tempuri.org/">
                          <user_id>{user_id}</user_id>
                          <id>0</id>
                          <su>{rs_acc}</su>
                          <sp>{rs_pass}</sp>
                          <invois_id>{out_inv_id}</invois_id>
                          {momsaxureba_xml}
                        </save_invoice_desc>
                      </soap:Body>
                    </soap:Envelope>
                """

                _logger.info(f'Sending SOAP request for line item: {line.name}')
                url = 'http://www.revenue.mof.ge/ntosservice/ntosservice.asmx'
                headers = {
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': 'http://tempuri.org/save_invoice_desc',
                }

                response = requests.post(url, data=soap_request.encode('utf-8'), headers=headers)
                _logger.info(f'Response for line item {line.name}: {response.text}')

            # Update status and related records
            factura_num = out_inv_id
            change_status_invoice = self.change_status_invoice(rs_pass, rs_acc, factura_num)

            combined_invoice = self.combined_invoice_id
            combined_invoice.write({'factura_num': factura_num})

            get_invoice = self.get_invoice(out_inv_id, rs_acc, rs_pass)
            combined_invoice.write({'get_invoice_id': get_invoice})

            _logger.info(f'Completed processing invoice with factura_num: {factura_num}')


        else:
            factura_num = self.save_invoice_momsaxureba(rs_acc, rs_pass, buyer_tin)
            _logger.info('Saved invoice with factura_num:', factura_num)

            # Save invoice description
            self.save_invoice_desc_momsaxureba(rs_acc, rs_pass, factura_num)

            _logger.info('Created new combined invoice record with factura_num:', factura_num)
            change_status_invoice = self.change_status_invoice(rs_pass, rs_acc, factura_num)
            get_invoice = self.get_invoice(factura_num, rs_acc, rs_pass)
            # Create a new combined.invoice.model record
            new_invoice = self.env['combined.invoice.model'].create({
                'factura_num': factura_num,  # Assigning the factura_num obtained
                # Add any other fields you need to set for this record
                'get_invoice_id': get_invoice,
            })
            # Update the combined_invoice_id on this sale order if needed
            self.combined_invoice_id = new_invoice.id

            ###write to invoice



    def button_factura(self):
        """Upload facturas - auto-detects single vs batch mode"""
        _logger.info(f'Executing button_factura for {len(self)} record(s)')
        
        # Single record mode - original behavior
        if len(self) == 1:
            for record in self:
                if not record.factura_num:
                    record.faqturebi()
                else:
                    raise UserError('ფაქტურა უკვე ატვირთულია')
        
        # Batch mode - process all records with error handling
        else:
            success_records = []
            error_records = []
            skipped_records = []
            
            for record in self:
                try:
                    if record.factura_num:
                        skipped_records.append((record.name, 'ფაქტურა უკვე ატვირთულია'))
                        continue
                        
                    record.faqturebi()
                    success_records.append(record.name)
                    self.env.cr.commit()  # Commit after each successful record
                    
                except Exception as e:
                    error_records.append((record.name, str(e)))
                    self.env.cr.rollback()  # Rollback failed record
                    _logger.exception(f"Error processing factura {record.name}")
            
            # Build result message
            messages = []
            if success_records:
                messages.append(f"✓ წარმატებით ატვირთულია ({len(success_records)}): {', '.join(success_records)}")
            if skipped_records:
                skipped_msg = '\n'.join([f"  - {name}: {reason}" for name, reason in skipped_records])
                messages.append(f"⊘ გამოტოვებულია ({len(skipped_records)}):\n{skipped_msg}")
            if error_records:
                error_msg = '\n'.join([f"  - {name}: {error}" for name, error in error_records])
                messages.append(f"✗ შეცდომები ({len(error_records)}):\n{error_msg}")
            
            final_message = '\n\n'.join(messages)
            
            if error_records and not success_records:
                raise UserError(final_message)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('ფაქტურების ატვირთვა დასრულდა'),
                    'message': final_message,
                    'type': 'success' if not error_records else 'warning',
                    'sticky': True,
                }
            }






