from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import requests
import xmltodict
import logging as _logger
import xml.etree.ElementTree as ET
from datetime import datetime

class FetchwaybillswizardCustom(models.TransientModel):
    _inherit = 'fetch.waybills.wizard'

    def fetch_waybills(self):
        try:
            date_str1 = self.date1.strftime('%Y-%m-%d')
            date_str2 = self.date2.strftime('%Y-%m-%d')
    
            # SOAP request URL and headers
            url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_waybills"
            }
    
            # SOAP body
            soap_body_waybills = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_waybills xmlns="http://tempuri.org/">
                  <su>{self.rs_acc}</su>
                  <sp>{self.rs_pass}</sp>
                  <itypes>2.3.6</itypes>
                  <buyer_tin/>
                  <statuses/>
                  <car_number/>
                  <begin_date_s xsi:nil="true"/>
                  <begin_date_e xsi:nil="true"/>
                  <create_date_s>{date_str1}T00:00:00+04:00</create_date_s>
                  <create_date_e>{date_str2}T23:59:59+04:00</create_date_e>
                  <delivery_date_s xsi:nil="true"/>
                  <delivery_date_e xsi:nil="true"/>
                  <full_amount xsi:nil="true"/>
                  <waybill_number/>
                  <close_date_s xsi:nil="true"/>
                  <close_date_e xsi:nil="true"/>
                  <s_user_ids/>
                  <comment/>
                </get_waybills>
              </soap:Body>
            </soap:Envelope>
            """
    
            # Perform request
            response = requests.post(url, data=soap_body_waybills.strip(), headers=headers)
            response.raise_for_status()  # Ensure we notice bad responses
            _logger.info("SOAP request successful, processing response")
    
            response_text = response.text
            _logger.info(f"SOAP response received: {response_text}")
    
            # Parse response
            data = xmltodict.parse(response_text)
            waybills = data.get('soap:Envelope', {}).get('soap:Body', {}).get('get_waybillsResponse', {}).get('get_waybillsResult', {}).get('WAYBILL_LIST', {}).get('WAYBILL', [])
    
            if not waybills:
                _logger.warning("No waybills found in the response")
                return {'type': 'ir.actions.act_window_close'}
    
            _logger.info(f"Found {len(waybills)} waybills to process")
    
            # Get models
            waybill_obj = self.env['waybill']
            waybill_line_obj = self.env['waybill.line']
            waybill_line_history_obj = self.env['waybill.line.history']
    
            for waybill_data in waybills:
                waybill_number = waybill_data.get('WAYBILL_NUMBER', '').strip()
                
                if not waybill_number:
                    _logger.warning(f"Skipping waybill with empty waybill_number: {waybill_data}")
                    continue  # Skip processing if waybill number is empty
    
                existing_waybill = waybill_obj.search([('waybill_number', '=', waybill_number)], limit=1)
                _logger.info(f"Processing waybill number: {waybill_number}")
    
                waybill_values = {
                    'waybill_number': waybill_data.get('WAYBILL_NUMBER', ''),
                    'create_date': waybill_data.get('CREATE_DATE', ''),
                    'buyer_tin': waybill_data.get('BUYER_TIN', ''),
                    'buyer_name': waybill_data.get('BUYER_NAME', ''),
                    'seller_name': waybill_data.get('SELLER_NAME', ''),
                    'seller_tin': waybill_data.get('SELLER_TIN', ''),
                    'start_address': waybill_data.get('START_ADDRESS', ''),
                    'end_address': waybill_data.get('END_ADDRESS', ''),
                    'transport_cost': waybill_data.get('TRANSPORT_COST', '0'),
                    'full_amount': waybill_data.get('FULL_AMOUNT', '0'),
                    'activate_date': waybill_data.get('ACTIVATE_DATE', ''),
                    's_user_id': waybill_data.get('S_USER_ID', ''),
                    'begin_date': waybill_data.get('BEGIN_DATE', ''),
                    'is_confirmed': waybill_data.get('IS_CONFIRMED', ''),
                    'is_corrected': waybill_data.get('IS_CORRECTED', ''),
                    'seller_st': waybill_data.get('SELLER_ST', ''),
                    'is_med': waybill_data.get('IS_MED', ''),
                    'waybill_comment': waybill_data.get('WAYBILL_COMMENT', ''),
                    'driver_tin': waybill_data.get('DRIVER_TIN', ''),
                    'driver_name': waybill_data.get('DRIVER_NAME', ''),
                    'car_number': waybill_data.get('CAR_NUMBER', ''),
                    'delivery_date': waybill_data.get('DELIVERY_DATE', ''),
                    'close_date': waybill_data.get('CLOSE_DATE', ''),
                    'invoice_id': waybill_data.get('INVOICE_ID', ''),
                    'waybill_id_number': waybill_data.get('ID', ''),
                    'waybill_type': waybill_data.get('TYPE', ''),
                    'error_text': 'რეალიზაცია',
                }
    
                if not existing_waybill:
                    # Create new waybill record if it doesn't exist
                    waybill_record = waybill_obj.create(waybill_values)
                    _logger.info(f"Waybill record created: {waybill_number}")
                else:
                    waybill_record = existing_waybill
                    _logger.info(f"Waybill record exists: {waybill_number}")
    
                waybill_id_number = waybill_data.get('ID', '')  # Get waybill_id_number for the next request
    
               
                url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_waybill"
                }
                payload = f"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                          <soap:Body>
                            <get_waybill xmlns="http://tempuri.org/">
                              <su>{self.rs_acc}</su>
                              <sp>{self.rs_pass}</sp>
                              <waybill_id>{waybill_id_number}</waybill_id>
                            </get_waybill>
                          </soap:Body>
                        </soap:Envelope>
                        """
                response = requests.post(url, data=payload, headers=headers)
                response.raise_for_status()
                response_text = response.text
                _logger.info(f"SOAP response for waybill details received: {response_text}")
                
                root = ET.fromstring(response_text)
                namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
    
                goods_list = []
                for goods in root.findall('.//GOODS', namespaces=namespace):
                    item = {
                        'w_name': goods.find('W_NAME').text.strip() if goods.find('W_NAME') is not None and goods.find('W_NAME').text else '',
                        'quantity': goods.find('QUANTITY').text.strip() if goods.find('QUANTITY') is not None and goods.find('QUANTITY').text else '',
                        'price': goods.find('PRICE').text.strip() if goods.find('PRICE') is not None and goods.find('PRICE').text else '',
                        'amount': goods.find('AMOUNT').text.strip() if goods.find('AMOUNT') is not None and goods.find('AMOUNT').text else '',
                        'bar_code': goods.find('BAR_CODE').text.strip() if goods.find('BAR_CODE') is not None and goods.find('BAR_CODE').text else '',
                        'a_id': goods.find('A_ID').text.strip() if goods.find('A_ID') is not None and goods.find('A_ID').text else '',
                        'vat_type': goods.find('VAT_TYPE').text.strip() if goods.find('VAT_TYPE') is not None and goods.find('VAT_TYPE').text else '',
                        'unit_id': goods.find('UNIT_ID').text.strip() if goods.find('UNIT_ID') is not None and goods.find('UNIT_ID').text else '',
                        'unit_txt': goods.find('UNIT_TXT').text.strip() if goods.find('UNIT_TXT') is not None and goods.find('UNIT_TXT').text else '',
                    }
                
                    unit_id = item.get('unit_id')
                    if unit_id in ['1', '2', '3', '4', '5', '7', '8', '9', '10', '11', '12', '13', '99']:
                        unit_value = unit_id  # Set the selection value directly
                    else:
                        unit_value = '99'  # Default to 'სხვა' if unknown
                    
                    # Update unit_id with the processed unit_value
                    item['unit_id'] = unit_value
                    
                    # Append the modified item with correct unit_id to the goods_list inside the loop
                    goods_list.append(item)


    
                # Fetch existing lines
                existing_lines = waybill_line_obj.search([('waybill_id', '=', waybill_record.id)])
                existing_line_names = existing_lines.mapped('w_name')
    
                if not goods_list:
                    _logger.warning(f"No goods list found for waybill number {waybill_number}")
                    continue
    
                new_line_names = [line['w_name'] for line in goods_list]
    
                if any(name not in existing_line_names for name in new_line_names):
                    _logger.info(f"Non-existent lines detected for waybill {waybill_number}, archiving existing lines")
                    # Archiving existing lines
                    history_vals_list = []
                    for line in existing_lines:
                        history_data = {
                            'product_id': line.product_id.id,
                            'w_name': line.w_name,
                            'quantity': line.quantity,
                            'price': line.price,
                            'amount': line.amount,
                            'bar_code': line.bar_code,
                            'a_id': line.a_id,
                            'vat_type': line.vat_type,
                            'status': line.status,
                            'quantity_fact': line.quantity_fact,
                            # Provide a value for `xarjang
                        }
                        history_vals_list.append(history_data)
                    if history_vals_list:
                        waybill_line_history_obj.create(history_vals_list)
    
                existing_lines.unlink()  # Remove existing lines
    
                # Create new lines
                # Prefetch products
                bar_codes = [item['bar_code'] for item in goods_list if item.get('bar_code')]
                products = self.env['product.product'].search([('barcode', 'in', bar_codes)])
                product_map = {p.barcode: p for p in products}

                waybill_line_vals_list = []
                for item in goods_list:
                    product = product_map.get(item['bar_code'])
                    line_values = {
                        'w_name': item['w_name'],
                        'quantity': item['quantity'],
                        'price': item['price'],
                        'amount': item['amount'],
                        'bar_code': item['bar_code'],
                        'a_id': item['a_id'],
                        'vat_type': item['vat_type'],
                        'waybill_id': waybill_record.id,
                        'product_id': product.id if product else False,
                        'unit_id': (product.unit_id if product else False) or item.get('unit_id'),
                        'unit_txt': (product.unit_txt if product else False) or item.get('unit_txt'),
                        'product_category_id': product.categ_id.id if product else False,
                    }
                    waybill_line_vals_list.append(line_values)
                
                if waybill_line_vals_list:
                    waybill_line_obj.create(waybill_line_vals_list)
    
                _logger.info(f"New lines created for waybill {waybill_number}")

            return {'type': 'ir.actions.act_window_close'}

        except requests.exceptions.RequestException as e:
            _logger.error(f"Request failed: {e}")
            raise UserError(f"Request failed: {e}")

        except UserError as ue:
            _logger.error(f"Error processing waybills: {ue}")
            raise

        except Exception as e:
            _logger.error(f"Unexpected error: {e}")
            raise UserError(f"Unexpected error occurred: {e}")



class Fetchwaybillswizard1Custom(models.TransientModel):
    _inherit = 'fetch.waybills.wizard1'

    def fetch_waybills_1(self):
        try:
            date_str1 = self.date1.strftime('%Y-%m-%d')
            date_str2 = self.date2.strftime('%Y-%m-%d')

            # SOAP request URL and headers
            url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "Host": "services.rs.ge",
                "Connection": "Keep-Alive",
                "Pragma": "no-cache"
            }

            # SOAP body
            soap_body_waybills = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_buyer_waybills xmlns="http://tempuri.org/">
                  <su>{self.rs_acc}</su>
                  <sp>{self.rs_pass}</sp>
                  <itypes>5</itypes>
                  <seller_tin/>
                  <statuses/>
                  <car_number/>
                  <begin_date_s xsi:nil="true"/>
                  <begin_date_e xsi:nil="true"/>
                  <create_date_s>{date_str1}T00:00:00+04:00</create_date_s>
                  <create_date_e>{date_str2}T23:59:59+04:00</create_date_e>
                  <driver_tin/>
                  <delivery_date_s xsi:nil="true"/>
                  <delivery_date_e xsi:nil="true"/>
                  <full_amount xsi:nil="true"/>
                  <waybill_number/>
                  <close_date_s xsi:nil="true"/>
                  <close_date_e xsi:nil="true"/>
                  <s_user_ids/>
                  <comment/>
                </get_buyer_waybills>
              </soap:Body>
            </soap:Envelope>
            """

            # Perform request
            response = requests.post(url, data=soap_body_waybills.strip(), headers=headers)
            response.raise_for_status()  # Ensure we notice bad responses
            _logger.info("SOAP request successful, processing response")
            
            response_text = response.text

            # Parse response
            data = xmltodict.parse(response_text)
            waybills = data.get('soap:Envelope', {}).get('soap:Body', {}).get('get_buyer_waybillsResponse', {}).get('get_buyer_waybillsResult', {}).get('WAYBILL_LIST', {}).get('WAYBILL', [])


            
            _logger.info(f"Found {len(waybills)} waybills to process")
            _logger.info(f"Parsed waybills: {waybills}")

            # Get models
            waybill_obj = self.env['waybill']

            for waybill_data in waybills:
                waybill_number = waybill_data.get('WAYBILL_NUMBER', '')
                existing_waybill = waybill_obj.search([('waybill_number', '=', waybill_number)])
                _logger.info(f"Processing waybill number: {waybill_number}")

                if not existing_waybill:
                    # Create waybill record
                    new_waybill = waybill_obj.create({
                        'waybill_number': waybill_data.get('WAYBILL_NUMBER', ''),
                        'create_date': waybill_data.get('CREATE_DATE', ''),
                        'buyer_tin': waybill_data.get('BUYER_TIN', ''),
                        'buyer_name': waybill_data.get('BUYER_NAME', ''),
                        'seller_name': waybill_data.get('SELLER_NAME', ''),
                        'seller_tin': waybill_data.get('SELLER_TIN', ''),
                        'start_address': waybill_data.get('START_ADDRESS', ''),
                        'end_address': waybill_data.get('END_ADDRESS', ''),
                        'transport_cost': waybill_data.get('TRANSPORT_COST', '0'),
                        'full_amount': waybill_data.get('FULL_AMOUNT', '0'),
                        'activate_date': waybill_data.get('ACTIVATE_DATE', ''),
                        's_user_id': waybill_data.get('S_USER_ID', ''),
                        'begin_date': waybill_data.get('BEGIN_DATE', ''),
                        'is_confirmed': waybill_data.get('IS_CONFIRMED', ''),
                        'is_corrected': waybill_data.get('IS_CORRECTED', ''),
                        'seller_st': waybill_data.get('SELLER_ST', ''),
                        'is_med': waybill_data.get('IS_MED', ''),
                        'waybill_comment': waybill_data.get('WAYBILL_COMMENT', ''),
                        'driver_tin': waybill_data.get('DRIVER_TIN', ''),
                        'driver_name': waybill_data.get('DRIVER_NAME', ''),
                        'car_number': waybill_data.get('CAR_NUMBER', ''),
                        'delivery_date': waybill_data.get('DELIVERY_DATE', ''),
                        'close_date': waybill_data.get('CLOSE_DATE', ''),
                        'invoice_id': waybill_data.get('INVOICE_ID', ''),
                        'waybill_id_number': waybill_data.get('ID',''),
                        'waybill_type': waybill_data.get('TYPE', ''),
                        'error_text': 'შესყიდვის დაბრუნება',

                    })
                    _logger.info(f"Waybill record created: {waybill_number}")

                    waybill_id_number = waybill_data.get('ID', '')  # Get waybill_id_number for the next request

                    url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
                    headers = {
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": "http://tempuri.org/get_waybill"
                    }
                    payload = f"""<?xml version="1.0" encoding="utf-8"?>
                            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                              <soap:Body>
                                <get_waybill xmlns="http://tempuri.org/">
                                  <su>{self.rs_acc}</su>
                                  <sp>{self.rs_pass}</sp>
                                  <waybill_id>{waybill_id_number}</waybill_id>
                                </get_waybill>
                              </soap:Body>
                            </soap:Envelope>
                            """
                    response = requests.post(url, data=payload, headers=headers)
                    response_text = response.text
                    root = ET.fromstring(response_text)
                    namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
                
                    goods_list = []
                    for goods in root.findall('.//GOODS', namespaces=namespace):
                        item = {
                            'w_name': goods.find('W_NAME').text.strip() if goods.find('W_NAME') is not None and goods.find('W_NAME').text else '',
                            'quantity': goods.find('QUANTITY').text.strip() if goods.find('QUANTITY') is not None and goods.find('QUANTITY').text else '',
                            'price': goods.find('PRICE').text.strip() if goods.find('PRICE') is not None and goods.find('PRICE').text else '',
                            'amount': goods.find('AMOUNT').text.strip() if goods.find('AMOUNT') is not None and goods.find('AMOUNT').text else '',
                            'bar_code': goods.find('BAR_CODE').text.strip() if goods.find('BAR_CODE') is not None and goods.find('BAR_CODE').text else '',
                            'a_id': goods.find('A_ID').text.strip() if goods.find('A_ID') is not None and goods.find('A_ID').text else '',
                            'vat_type': goods.find('VAT_TYPE').text.strip() if goods.find('VAT_TYPE') is not None and goods.find('VAT_TYPE').text else '',
                            'unit_id': goods.find('UNIT_ID').text.strip() if goods.find('UNIT_ID') is not None and goods.find('UNIT_ID').text else '',
                            'unit_txt': goods.find('UNIT_TXT').text.strip() if goods.find('UNIT_TXT') is not None and goods.find('UNIT_TXT').text else '',
                        }
                    
                        unit_id = item.get('unit_id')
                        if unit_id in ['1', '2', '3', '4', '5', '7', '8', '9', '10', '11', '12', '13', '99']:
                            unit_value = unit_id  # Set the selection value directly
                        else:
                            unit_value = '99'  # Default to 'სხვა' if unknown
                        
                        # Update unit_id with the processed unit_value
                        item['unit_id'] = unit_value
                        
                        # Append the modified item with correct unit_id to the goods_list inside the loop
                        goods_list.append(item)


                
                    _logger.info(f"Parsed {len(goods_list)} items from the API response")
                
                    waybill_line_vals = []
                    waybill_record = waybill_obj.search([('waybill_id_number', '=', waybill_id_number)], limit=1)
                    if waybill_record:
                        _logger.info(f"Updating existing waybill with ID: {waybill_record.id}")
                        waybill_record.line_ids.unlink()  # Remove existing lines
                    else:
                        _logger.info(f"Creating new waybill record for waybill number: {waybill_id_number}")
                        waybill_record = waybill_obj.create({'waybill_id_number': waybill_id_number})
                
                    # Prefetch strategy
                    bar_codes = [item['bar_code'] for item in goods_list if item.get('bar_code')]
                    
                    # 1. Partner is already found per waybill iteration
                    seller_tin = waybill_data.get('SELLER_TIN', '')
                    partner = self.env['res.partner'].search([('vat', '=', seller_tin)], limit=1)

                    supplier_info_map = {}
                    if partner and bar_codes:
                        supplier_infos = self.env['product.supplierinfo'].search([
                            ('partner_id', '=', partner.id),
                            ('product_code', 'in', bar_codes)
                        ])
                        supplier_info_map = {si.product_code: si for si in supplier_infos}


                    # 2. Products (Strict Supplier Info Only)
                    # No direct product lookup

                    waybill_line_vals_list = []
                    for item in goods_list:
                        # Link to product if buyer TIN and barcode match
                        found_product = False
                        product_id = False
                        koef = 1.0
                        category_id = False
                        unit_id_val = item.get('unit_id')
                        unit_txt_val = item.get('unit_txt')

                        # Check supplier info first
                        supplier_info = supplier_info_map.get(item['bar_code'])
                        if supplier_info and supplier_info.product_tmpl_id:
                            product_id = supplier_info.product_tmpl_id.id
                            koef = supplier_info.koef or 1.0
                            category_id = supplier_info.product_tmpl_id.categ_id.id
                            unit_id_val = supplier_info.product_tmpl_id.unit_id or unit_id_val
                            unit_txt_val = supplier_info.product_tmpl_id.unit_txt or unit_txt_val
                            found_product = True


                        if found_product:
                            _logger.info(f"Linking waybill line to product ID: {product_id}")
                            waybill_line_vals_list.append({
                                'waybill_id': waybill_record.id,
                                **item,
                                'product_id': product_id,
                                'koef': koef,
                                'product_category_id': category_id,
                                'unit_id': unit_id_val or item.get('unit_id'),
                                'unit_txt': unit_txt_val or item.get('unit_txt'),
                            })
                        else:
                            waybill_line_vals_list.append({
                                'waybill_id': waybill_record.id,
                                **item
                            })
                
                    if waybill_line_vals_list:
                        self.env['waybill.line'].create(waybill_line_vals_list)
                    _logger.info(f"Created {len(waybill_line_vals)} waybill lines for waybill ID: {waybill_id_number}")

        except requests.RequestException as e:
            raise UserError(f"Error in SOAP request: {e}")

        except ET.ParseError as e:
            raise UserError(f"Error parsing SOAP response: {e}")

        except Exception as e:
            raise UserError(f"An unexpected error occurred: {e}")

        return {'type': 'ir.actions.act_window_close'}



class Fetchwaybillswizard3Custom(models.TransientModel):
    _inherit = 'fetch.waybills.wizard3'

    def fetch_waybills_3(self):
        try:
            date_str1 = self.date1.strftime('%Y-%m-%d')
            date_str2 = self.date2.strftime('%Y-%m-%d')
    
            # SOAP request URL and headers
            url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_waybills"
            }
    
            # SOAP body
            soap_body_waybills = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_waybills xmlns="http://tempuri.org/">
                  <su>{self.rs_acc}</su>
                  <sp>{self.rs_pass}</sp>
                  <itypes>5</itypes>
                  <buyer_tin/>
                  <statuses/>
                  <car_number/>
                  <begin_date_s xsi:nil="true"/>
                  <begin_date_e xsi:nil="true"/>
                  <create_date_s>{date_str1}T00:00:00+04:00</create_date_s>
                  <create_date_e>{date_str2}T23:59:59+04:00</create_date_e>
                  <delivery_date_s xsi:nil="true"/>
                  <delivery_date_e xsi:nil="true"/>
                  <full_amount xsi:nil="true"/>
                  <waybill_number/>
                  <close_date_s xsi:nil="true"/>
                  <close_date_e xsi:nil="true"/>
                  <s_user_ids/>
                  <comment/>
                </get_waybills>
              </soap:Body>
            </soap:Envelope>
            """
    
            # Perform request
            response = requests.post(url, data=soap_body_waybills.strip(), headers=headers)
            response.raise_for_status()  # Ensure we notice bad responses
            _logger.info("SOAP request successful, processing response")
    
            response_text = response.text
            _logger.info(f"SOAP response received: {response_text}")
    
            # Parse response
            data = xmltodict.parse(response_text)
            waybills = data.get('soap:Envelope', {}).get('soap:Body', {}).get('get_waybillsResponse', {}).get('get_waybillsResult', {}).get('WAYBILL_LIST', {}).get('WAYBILL', [])
    
            if not waybills:
                _logger.warning("No waybills found in the response")
                return {'type': 'ir.actions.act_window_close'}
    
            _logger.info(f"Found {len(waybills)} waybills to process")
    
            # Get models
            waybill_obj = self.env['waybill']
            waybill_line_obj = self.env['waybill.line']
            waybill_line_history_obj = self.env['waybill.line.history']
    
            for waybill_data in waybills:
                waybill_number = waybill_data.get('WAYBILL_NUMBER', '').strip()
                
                if not waybill_number:
                    _logger.warning(f"Skipping waybill with empty waybill_number: {waybill_data}")
                    continue  # Skip processing if waybill number is empty
    
                existing_waybill = waybill_obj.search([('waybill_number', '=', waybill_number)], limit=1)
                _logger.info(f"Processing waybill number: {waybill_number}")
    
                waybill_values = {
                    'waybill_number': waybill_data.get('WAYBILL_NUMBER', ''),
                    'create_date': waybill_data.get('CREATE_DATE', ''),
                    'buyer_tin': waybill_data.get('BUYER_TIN', ''),
                    'buyer_name': waybill_data.get('BUYER_NAME', ''),
                    'seller_name': waybill_data.get('SELLER_NAME', ''),
                    'seller_tin': waybill_data.get('SELLER_TIN', ''),
                    'start_address': waybill_data.get('START_ADDRESS', ''),
                    'end_address': waybill_data.get('END_ADDRESS', ''),
                    'transport_cost': waybill_data.get('TRANSPORT_COST', '0'),
                    'full_amount': waybill_data.get('FULL_AMOUNT', '0'),
                    'activate_date': waybill_data.get('ACTIVATE_DATE', ''),
                    's_user_id': waybill_data.get('S_USER_ID', ''),
                    'begin_date': waybill_data.get('BEGIN_DATE', ''),
                    'is_confirmed': waybill_data.get('IS_CONFIRMED', ''),
                    'is_corrected': waybill_data.get('IS_CORRECTED', ''),
                    'seller_st': waybill_data.get('SELLER_ST', ''),
                    'is_med': waybill_data.get('IS_MED', ''),
                    'waybill_comment': waybill_data.get('WAYBILL_COMMENT', ''),
                    'driver_tin': waybill_data.get('DRIVER_TIN', ''),
                    'driver_name': waybill_data.get('DRIVER_NAME', ''),
                    'car_number': waybill_data.get('CAR_NUMBER', ''),
                    'delivery_date': waybill_data.get('DELIVERY_DATE', ''),
                    'close_date': waybill_data.get('CLOSE_DATE', ''),
                    'invoice_id': waybill_data.get('INVOICE_ID', ''),
                    'waybill_id_number': waybill_data.get('ID', ''),
                    'waybill_type': waybill_data.get('TYPE', ''),
                    'error_text': 'რეალიზაციის დაბრუნება',
                }
    
                if not existing_waybill:
                    # Create new waybill record if it doesn't exist
                    waybill_record = waybill_obj.create(waybill_values)
                    _logger.info(f"Waybill record created: {waybill_number}")
                else:
                    waybill_record = existing_waybill
                    _logger.info(f"Waybill record exists: {waybill_number}")
    
                waybill_id_number = waybill_data.get('ID', '')  # Get waybill_id_number for the next request
    
             
                url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_waybill"
                }
                payload = f"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                          <soap:Body>
                            <get_waybill xmlns="http://tempuri.org/">
                              <su>{self.rs_acc}</su>
                              <sp>{self.rs_pass}</sp>
                              <waybill_id>{waybill_id_number}</waybill_id>
                            </get_waybill>
                          </soap:Body>
                        </soap:Envelope>
                        """
                response = requests.post(url, data=payload, headers=headers)
                response.raise_for_status()
                response_text = response.text
                _logger.info(f"SOAP response for waybill details received: {response_text}")
                
                root = ET.fromstring(response_text)
                namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
    
                goods_list = []
                for goods in root.findall('.//GOODS', namespaces=namespace):
                    item = {
                        'w_name': goods.find('W_NAME').text.strip() if goods.find('W_NAME') is not None and goods.find('W_NAME').text else '',
                        'quantity': goods.find('QUANTITY').text.strip() if goods.find('QUANTITY') is not None and goods.find('QUANTITY').text else '',
                        'price': goods.find('PRICE').text.strip() if goods.find('PRICE') is not None and goods.find('PRICE').text else '',
                        'amount': goods.find('AMOUNT').text.strip() if goods.find('AMOUNT') is not None and goods.find('AMOUNT').text else '',
                        'bar_code': goods.find('BAR_CODE').text.strip() if goods.find('BAR_CODE') is not None and goods.find('BAR_CODE').text else '',
                        'a_id': goods.find('A_ID').text.strip() if goods.find('A_ID') is not None and goods.find('A_ID').text else '',
                        'vat_type': goods.find('VAT_TYPE').text.strip() if goods.find('VAT_TYPE') is not None and goods.find('VAT_TYPE').text else '',
                        'unit_id': goods.find('UNIT_ID').text.strip() if goods.find('UNIT_ID') is not None and goods.find('UNIT_ID').text else '',
                        'unit_txt': goods.find('UNIT_TXT').text.strip() if goods.find('UNIT_TXT') is not None and goods.find('UNIT_TXT').text else '',
                    }
                
                    unit_id = item.get('unit_id')
                    if unit_id in ['1', '2', '3', '4', '5', '7', '8', '9', '10', '11', '12', '13', '99']:
                        unit_value = unit_id  # Set the selection value directly
                    else:
                        unit_value = '99'  # Default to 'სხვა' if unknown
                    
                    # Update unit_id with the processed unit_value
                    item['unit_id'] = unit_value
                    
                    # Append the modified item with correct unit_id to the goods_list inside the loop
                    goods_list.append(item)

    
                # Fetch existing lines
                existing_lines = waybill_line_obj.search([('waybill_id', '=', waybill_record.id)])
                existing_line_names = existing_lines.mapped('w_name')
    
                if not goods_list:
                    _logger.warning(f"No goods list found for waybill number {waybill_number}")
                    continue
    
                new_line_names = [line['w_name'] for line in goods_list]
    
                if any(name not in existing_line_names for name in new_line_names):
                    _logger.info(f"Non-existent lines detected for waybill {waybill_number}, archiving existing lines")
                    # Archiving existing lines
                    history_vals_list = []
                    for line in existing_lines:
                        history_data = {
                            'product_id': line.product_id.id,
                            'w_name': line.w_name,
                            'quantity': line.quantity,
                            'price': line.price,
                            'amount': line.amount,
                            'bar_code': line.bar_code,
                            'a_id': line.a_id,
                            'vat_type': line.vat_type,
                            'status': line.status,
                            'quantity_fact': line.quantity_fact,
                            # Provide a value for `xarjang
                        }
                        history_vals_list.append(history_data)
                    if history_vals_list:
                        waybill_line_history_obj.create(history_vals_list)
    
                existing_lines.unlink()  # Remove existing lines
    
                # Create new lines
                # Prefetch products
                bar_codes = [item['bar_code'] for item in goods_list if item.get('bar_code')]
                products = self.env['product.product'].search([('barcode', 'in', bar_codes)])
                product_map = {p.barcode: p for p in products}

                waybill_line_vals_list = []
                for item in goods_list:
                    product = product_map.get(item['bar_code'])
                    line_values = {
                        'w_name': item['w_name'],
                        'quantity': item['quantity'],
                        'price': item['price'],
                        'amount': item['amount'],
                        'bar_code': item['bar_code'],
                        'a_id': item['a_id'],
                        'vat_type': item['vat_type'],
                        'waybill_id': waybill_record.id,
                        'product_id': product.id if product else False,
                        'unit_id': (product.unit_id if product else False) or item.get('unit_id'),
                        'unit_txt': (product.unit_txt if product else False) or item.get('unit_txt'),
                        'product_category_id': product.categ_id.id if product else False,
                    }
                    waybill_line_vals_list.append(line_values)
                
                if waybill_line_vals_list:
                    waybill_line_obj.create(waybill_line_vals_list)
    
                _logger.info(f"New lines created for waybill {waybill_number}")

            return {'type': 'ir.actions.act_window_close'}

        except requests.exceptions.RequestException as e:
            _logger.error(f"Request failed: {e}")
            raise UserError(f"Request failed: {e}")

        except UserError as ue:
            _logger.error(f"Error processing waybills: {ue}")
            raise

        except Exception as e:
            _logger.error(f"Unexpected error: {e}")
            raise UserError(f"Unexpected error occurred: {e}")




class Fetchwaybillswizard4Custom(models.TransientModel):
    _inherit = 'fetch.waybills.wizard4'

    def fetch_waybills(self):
        try:
            date_str1 = self.date1.strftime('%Y-%m-%d')
            date_str2 = self.date2.strftime('%Y-%m-%d')

            # SOAP request URL and headers
            url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "Host": "services.rs.ge",
                "Connection": "Keep-Alive",
                "Pragma": "no-cache"
            }

            # SOAP body
            soap_body_waybills = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_buyer_waybills xmlns="http://tempuri.org/">
                  <su>{self.rs_acc}</su>
                  <sp>{self.rs_pass}</sp>
                  <itypes>2.3.6</itypes>
                  <seller_tin/>
                  <statuses/>
                  <car_number/>
                  <begin_date_s xsi:nil="true"/>
                  <begin_date_e xsi:nil="true"/>
                  <create_date_s>{date_str1}T00:00:00+04:00</create_date_s>
                  <create_date_e>{date_str2}T23:59:59+04:00</create_date_e>
                  <driver_tin/>
                  <delivery_date_s xsi:nil="true"/>
                  <delivery_date_e xsi:nil="true"/>
                  <full_amount xsi:nil="true"/>
                  <waybill_number/>
                  <close_date_s xsi:nil="true"/>
                  <close_date_e xsi:nil="true"/>
                  <s_user_ids/>
                  <comment/>
                </get_buyer_waybills>
              </soap:Body>
            </soap:Envelope>
            """

            # Perform request
            response = requests.post(url, data=soap_body_waybills.strip(), headers=headers)
            response.raise_for_status()  # Ensure we notice bad responses
            _logger.info("SOAP request successful, processing response")
            
            response_text = response.text

            # Parse response
            data = xmltodict.parse(response_text)
            waybills = data['soap:Envelope']['soap:Body']['get_buyer_waybillsResponse']['get_buyer_waybillsResult']['WAYBILL_LIST']['WAYBILL']
            _logger.info(f"Found {len(waybills)} waybills to process")

            # Get models
            waybill_obj = self.env['waybill']

            for waybill_data in waybills:
                waybill_number = waybill_data.get('WAYBILL_NUMBER', '')
                existing_waybill = waybill_obj.search([('waybill_number', '=', waybill_number)])
                _logger.info(f"Processing waybill number: {waybill_number}")

                if not existing_waybill:
                    # Create waybill record
                    new_waybill = waybill_obj.create({
                        'waybill_number': waybill_data.get('WAYBILL_NUMBER', ''),
                        'create_date': waybill_data.get('CREATE_DATE', ''),
                        'buyer_tin': waybill_data.get('BUYER_TIN', ''),
                        'buyer_name': waybill_data.get('BUYER_NAME', ''),
                        'seller_name': waybill_data.get('SELLER_NAME', ''),
                        'seller_tin': waybill_data.get('SELLER_TIN', ''),
                        'start_address': waybill_data.get('START_ADDRESS', ''),
                        'end_address': waybill_data.get('END_ADDRESS', ''),
                        'transport_cost': waybill_data.get('TRANSPORT_COST', '0'),
                        'full_amount': waybill_data.get('FULL_AMOUNT', '0'),
                        'activate_date': waybill_data.get('ACTIVATE_DATE', ''),
                        's_user_id': waybill_data.get('S_USER_ID', ''),
                        'begin_date': waybill_data.get('BEGIN_DATE', ''),
                        'is_confirmed': waybill_data.get('IS_CONFIRMED', ''),
                        'is_corrected': waybill_data.get('IS_CORRECTED', ''),
                        'seller_st': waybill_data.get('SELLER_ST', ''),
                        'is_med': waybill_data.get('IS_MED', ''),
                        'waybill_comment': waybill_data.get('WAYBILL_COMMENT', ''),
                        'driver_tin': waybill_data.get('DRIVER_TIN', ''),
                        'driver_name': waybill_data.get('DRIVER_NAME', ''),
                        'car_number': waybill_data.get('CAR_NUMBER', ''),
                        'delivery_date': waybill_data.get('DELIVERY_DATE', ''),
                        'close_date': waybill_data.get('CLOSE_DATE', ''),
                        'invoice_id': waybill_data.get('INVOICE_ID', ''),
                        'waybill_id_number': waybill_data.get('ID',''),
                        'waybill_type': waybill_data.get('TYPE', ''),
                        'error_text': 'შესყიდვა',

                    })
                    _logger.info(f"Waybill record created: {waybill_number}")

                    waybill_id_number = waybill_data.get('ID', '')  # Get waybill_id_number for the next request


                    url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
                    headers = {
                        "Content-Type": "text/xml; charset=utf-8",
                        "SOAPAction": "http://tempuri.org/get_waybill"
                    }
                    payload = f"""<?xml version="1.0" encoding="utf-8"?>
                            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                              <soap:Body>
                                <get_waybill xmlns="http://tempuri.org/">
                                  <su>{self.rs_acc}</su>
                                  <sp>{self.rs_pass}</sp>
                                  <waybill_id>{waybill_id_number}</waybill_id>
                                </get_waybill>
                              </soap:Body>
                            </soap:Envelope>
                            """
                    response = requests.post(url, data=payload, headers=headers)
                    response_text = response.text
                    root = ET.fromstring(response_text)
                    namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
                
                    goods_list = []
                    for goods in root.findall('.//GOODS', namespaces=namespace):
                        item = {
                            'w_name': goods.find('W_NAME').text.strip() if goods.find('W_NAME') is not None and goods.find('W_NAME').text else '',
                            'quantity': goods.find('QUANTITY').text.strip() if goods.find('QUANTITY') is not None and goods.find('QUANTITY').text else '',
                            'price': goods.find('PRICE').text.strip() if goods.find('PRICE') is not None and goods.find('PRICE').text else '',
                            'amount': goods.find('AMOUNT').text.strip() if goods.find('AMOUNT') is not None and goods.find('AMOUNT').text else '',
                            'bar_code': goods.find('BAR_CODE').text.strip() if goods.find('BAR_CODE') is not None and goods.find('BAR_CODE').text else '',
                            'a_id': goods.find('A_ID').text.strip() if goods.find('A_ID') is not None and goods.find('A_ID').text else '',
                            'vat_type': goods.find('VAT_TYPE').text.strip() if goods.find('VAT_TYPE') is not None and goods.find('VAT_TYPE').text else '',
                            'unit_id': goods.find('UNIT_ID').text.strip() if goods.find('UNIT_ID') is not None and goods.find('UNIT_ID').text else '',
                            'unit_txt': goods.find('UNIT_TXT').text.strip() if goods.find('UNIT_TXT') is not None and goods.find('UNIT_TXT').text else '',
                        }
                    
                        unit_id = item.get('unit_id')
                        if unit_id in ['1', '2', '3', '4', '5', '7', '8', '9', '10', '11', '12', '13', '99']:
                            unit_value = unit_id  # Set the selection value directly
                        else:
                            unit_value = '99'  # Default to 'სხვა' if unknown
                        
                        # Update unit_id with the processed unit_value
                        item['unit_id'] = unit_value
                        
                        # Append the modified item with correct unit_id to the goods_list inside the loop
                        goods_list.append(item)

                
                    _logger.info(f"Parsed {len(goods_list)} items from the API response")
                
                    waybill_line_vals = []
                    waybill_record = waybill_obj.search([('waybill_id_number', '=', waybill_id_number)], limit=1)
                    if waybill_record:
                        _logger.info(f"Updating existing waybill with ID: {waybill_record.id}")
                        waybill_record.line_ids.unlink()  # Remove existing lines
                    else:
                        _logger.info(f"Creating new waybill record for waybill number: {waybill_id_number}")
                        waybill_record = waybill_obj.create({'waybill_id_number': waybill_id_number})
                
                    # Prefetch strategy
                    bar_codes = [item['bar_code'] for item in goods_list if item.get('bar_code')]
                    
                    # 1. Partner is already found per waybill iteration
                    seller_tin = waybill_data.get('SELLER_TIN', '')
                    partner = self.env['res.partner'].search([('vat', '=', seller_tin)], limit=1)

                    supplier_info_map = {}
                    if partner and bar_codes:
                        supplier_infos = self.env['product.supplierinfo'].search([
                            ('partner_id', '=', partner.id),
                            ('product_code', 'in', bar_codes)
                        ])
                        supplier_info_map = {si.product_code: si for si in supplier_infos}


                    # 2. Products (Strict Supplier Info Only)
                    # No direct product lookup

                    waybill_line_vals_list = []
                    for item in goods_list:
                        # Link to product if buyer TIN and barcode match
                        found_product = False
                        product_id = False
                        koef = 1.0
                        category_id = False
                        unit_id_val = item.get('unit_id')
                        unit_txt_val = item.get('unit_txt')

                        # Check supplier info first
                        supplier_info = supplier_info_map.get(item['bar_code'])
                        if supplier_info and supplier_info.product_tmpl_id:
                            product_id = supplier_info.product_tmpl_id.id
                            koef = supplier_info.koef or 1.0
                            category_id = supplier_info.product_tmpl_id.categ_id.id
                            unit_id_val = supplier_info.product_tmpl_id.unit_id or unit_id_val
                            unit_txt_val = supplier_info.product_tmpl_id.unit_txt or unit_txt_val
                            found_product = True


                        if found_product:
                            _logger.info(f"Linking waybill line to product ID: {product_id}")
                            waybill_line_vals_list.append({
                                'waybill_id': waybill_record.id,
                                **item,
                                'product_id': product_id,
                                'koef': koef,
                                'product_category_id': category_id,
                                'unit_id': unit_id_val or item.get('unit_id'),
                                'unit_txt': unit_txt_val or item.get('unit_txt'),
                            })
                        else:
                            waybill_line_vals_list.append({
                                'waybill_id': waybill_record.id,
                                **item
                            })
                
                    if waybill_line_vals_list:
                        self.env['waybill.line'].create(waybill_line_vals_list)
                    _logger.info(f"Created {len(waybill_line_vals)} waybill lines for waybill ID: {waybill_id_number}")

        except requests.RequestException as e:
            raise UserError(f"Error in SOAP request: {e}")

        except ET.ParseError as e:
            raise UserError(f"Error parsing SOAP response: {e}")

        except Exception as e:
            raise UserError(f"An unexpected error occurred: {e}")

        return {'type': 'ir.actions.act_window_close'}



class Fetchwaybillswizard5Custom(models.TransientModel):
    _inherit = 'fetch.waybills.wizard5'

    def fetch_waybills(self):
        try:
            date_str1 = self.date1.strftime('%Y-%m-%d')
            date_str2 = self.date2.strftime('%Y-%m-%d')
    
            # SOAP request URL and headers
            url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
            headers = {
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": "http://tempuri.org/get_waybills"
            }
    
            # SOAP body
            soap_body_waybills = f"""
            <?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                           xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                           xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_waybills xmlns="http://tempuri.org/">
                  <su>{self.rs_acc}</su>
                  <sp>{self.rs_pass}</sp>
                  <itypes>1</itypes>
                  <buyer_tin/>
                  <statuses/>
                  <car_number/>
                  <begin_date_s xsi:nil="true"/>
                  <begin_date_e xsi:nil="true"/>
                  <create_date_s>{date_str1}T00:00:00+04:00</create_date_s>
                  <create_date_e>{date_str2}T23:59:59+04:00</create_date_e>
                  <delivery_date_s xsi:nil="true"/>
                  <delivery_date_e xsi:nil="true"/>
                  <full_amount xsi:nil="true"/>
                  <waybill_number/>
                  <close_date_s xsi:nil="true"/>
                  <close_date_e xsi:nil="true"/>
                  <s_user_ids/>
                  <comment/>
                </get_waybills>
              </soap:Body>
            </soap:Envelope>
            """
    
            # Perform request
            response = requests.post(url, data=soap_body_waybills.strip(), headers=headers)
            response.raise_for_status()  # Ensure we notice bad responses
            _logger.info("SOAP request successful, processing response")
    
            response_text = response.text
            _logger.info(f"SOAP response received: {response_text}")
    
            # Parse response
            data = xmltodict.parse(response_text)
            waybills = data.get('soap:Envelope', {}).get('soap:Body', {}).get('get_waybillsResponse', {}).get('get_waybillsResult', {}).get('WAYBILL_LIST', {}).get('WAYBILL', [])
    
            if not waybills:
                _logger.warning("No waybills found in the response")
                return {'type': 'ir.actions.act_window_close'}
    
            _logger.info(f"Found {len(waybills)} waybills to process")
    
            # Get models
            waybill_obj = self.env['waybill']
            waybill_line_obj = self.env['waybill.line']
            waybill_line_history_obj = self.env['waybill.line.history']
    
            for waybill_data in waybills:
                waybill_number = waybill_data.get('WAYBILL_NUMBER', '').strip()
                
                if not waybill_number:
                    _logger.warning(f"Skipping waybill with empty waybill_number: {waybill_data}")
                    continue  # Skip processing if waybill number is empty
    
                existing_waybill = waybill_obj.search([('waybill_number', '=', waybill_number)], limit=1)
                _logger.info(f"Processing waybill number: {waybill_number}")
    
                waybill_values = {
                    'waybill_number': waybill_data.get('WAYBILL_NUMBER', ''),
                    'create_date': waybill_data.get('CREATE_DATE', ''),
                    'buyer_tin': waybill_data.get('BUYER_TIN', ''),
                    'buyer_name': waybill_data.get('BUYER_NAME', ''),
                    'seller_name': waybill_data.get('SELLER_NAME', ''),
                    'seller_tin': waybill_data.get('SELLER_TIN', ''),
                    'start_address': waybill_data.get('START_ADDRESS', ''),
                    'end_address': waybill_data.get('END_ADDRESS', ''),
                    'transport_cost': waybill_data.get('TRANSPORT_COST', '0'),
                    'full_amount': waybill_data.get('FULL_AMOUNT', '0'),
                    'activate_date': waybill_data.get('ACTIVATE_DATE', ''),
                    's_user_id': waybill_data.get('S_USER_ID', ''),
                    'begin_date': waybill_data.get('BEGIN_DATE', ''),
                    'is_confirmed': waybill_data.get('IS_CONFIRMED', ''),
                    'is_corrected': waybill_data.get('IS_CORRECTED', ''),
                    'seller_st': waybill_data.get('SELLER_ST', ''),
                    'is_med': waybill_data.get('IS_MED', ''),
                    'waybill_comment': waybill_data.get('WAYBILL_COMMENT', ''),
                    'driver_tin': waybill_data.get('DRIVER_TIN', ''),
                    'driver_name': waybill_data.get('DRIVER_NAME', ''),
                    'car_number': waybill_data.get('CAR_NUMBER', ''),
                    'delivery_date': waybill_data.get('DELIVERY_DATE', ''),
                    'close_date': waybill_data.get('CLOSE_DATE', ''),
                    'invoice_id': waybill_data.get('INVOICE_ID', ''),
                    'waybill_id_number': waybill_data.get('ID', ''),
                    'waybill_type': waybill_data.get('TYPE', ''),
                    'error_text': 'შიდა გადაზიდვა',
                }
    
                if not existing_waybill:
                    # Create new waybill record if it doesn't exist
                    waybill_record = waybill_obj.create(waybill_values)
                    _logger.info(f"Waybill record created: {waybill_number}")
                else:
                    waybill_record = existing_waybill
                    _logger.info(f"Waybill record exists: {waybill_number}")
    
                waybill_id_number = waybill_data.get('ID', '')  # Get waybill_id_number for the next request
    

                url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
                headers = {
                    "Content-Type": "text/xml; charset=utf-8",
                    "SOAPAction": "http://tempuri.org/get_waybill"
                }
                payload = f"""<?xml version="1.0" encoding="utf-8"?>
                        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                          <soap:Body>
                            <get_waybill xmlns="http://tempuri.org/">
                              <su>{self.rs_acc}</su>
                              <sp>{self.rs_pass}</sp>
                              <waybill_id>{waybill_id_number}</waybill_id>
                            </get_waybill>
                          </soap:Body>
                        </soap:Envelope>
                        """
                response = requests.post(url, data=payload, headers=headers)
                response.raise_for_status()
                response_text = response.text
                _logger.info(f"SOAP response for waybill details received: {response_text}")
                
                root = ET.fromstring(response_text)
                namespace = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
    
                goods_list = []
                for goods in root.findall('.//GOODS', namespaces=namespace):
                    item = {
                        'w_name': goods.find('W_NAME').text.strip() if goods.find('W_NAME') is not None and goods.find('W_NAME').text else '',
                        'quantity': goods.find('QUANTITY').text.strip() if goods.find('QUANTITY') is not None and goods.find('QUANTITY').text else '',
                        'price': goods.find('PRICE').text.strip() if goods.find('PRICE') is not None and goods.find('PRICE').text else '',
                        'amount': goods.find('AMOUNT').text.strip() if goods.find('AMOUNT') is not None and goods.find('AMOUNT').text else '',
                        'bar_code': goods.find('BAR_CODE').text.strip() if goods.find('BAR_CODE') is not None and goods.find('BAR_CODE').text else '',
                        'a_id': goods.find('A_ID').text.strip() if goods.find('A_ID') is not None and goods.find('A_ID').text else '',
                        'vat_type': goods.find('VAT_TYPE').text.strip() if goods.find('VAT_TYPE') is not None and goods.find('VAT_TYPE').text else '',
                        'unit_id': goods.find('UNIT_ID').text.strip() if goods.find('UNIT_ID') is not None and goods.find('UNIT_ID').text else '',
                        'unit_txt': goods.find('UNIT_TXT').text.strip() if goods.find('UNIT_TXT') is not None and goods.find('UNIT_TXT').text else '',
                    }
                
                    unit_id = item.get('unit_id')
                    if unit_id in ['1', '2', '3', '4', '5', '7', '8', '9', '10', '11', '12', '13', '99']:
                        unit_value = unit_id  # Set the selection value directly
                    else:
                        unit_value = '99'  # Default to 'სხვა' if unknown
                    
                    # Update unit_id with the processed unit_value
                    item['unit_id'] = unit_value
                    
                    # Append the modified item with correct unit_id to the goods_list inside the loop
                    goods_list.append(item)


    
                # Fetch existing lines
                existing_lines = waybill_line_obj.search([('waybill_id', '=', waybill_record.id)])
                existing_line_names = existing_lines.mapped('w_name')
    
                if not goods_list:
                    _logger.warning(f"No goods list found for waybill number {waybill_number}")
                    continue
    
                new_line_names = [line['w_name'] for line in goods_list]
    
                if any(name not in existing_line_names for name in new_line_names):
                    _logger.info(f"Non-existent lines detected for waybill {waybill_number}, archiving existing lines")
                    # Archiving existing lines
                    history_vals_list = []
                    for line in existing_lines:
                        history_data = {
                            'product_id': line.product_id.id,
                            'w_name': line.w_name,
                            'quantity': line.quantity,
                            'price': line.price,
                            'amount': line.amount,
                            'bar_code': line.bar_code,
                            'a_id': line.a_id,
                            'vat_type': line.vat_type,
                            'status': line.status,
                            'quantity_fact': line.quantity_fact,
                            # Provide a value for `xarjang
                        }
                        history_vals_list.append(history_data)
                    if history_vals_list:
                        waybill_line_history_obj.create(history_vals_list)
    
                existing_lines.unlink()  # Remove existing lines
    
                # Create new lines
                # Prefetch products
                bar_codes = [item['bar_code'] for item in goods_list if item.get('bar_code')]
                products = self.env['product.product'].search([('barcode', 'in', bar_codes)])
                product_map = {p.barcode: p for p in products}

                waybill_line_vals_list = []
                for item in goods_list:
                    product = product_map.get(item['bar_code'])
                    line_values = {
                        'w_name': item['w_name'],
                        'quantity': item['quantity'],
                        'price': item['price'],
                        'amount': item['amount'],
                        'bar_code': item['bar_code'],
                        'a_id': item['a_id'],
                        'vat_type': item['vat_type'],
                        'waybill_id': waybill_record.id,
                        'product_id': product.id if product else False,
                        'unit_id': (product.unit_id if product else False) or item.get('unit_id'),
                        'unit_txt': (product.unit_txt if product else False) or item.get('unit_txt'),
                        'product_category_id': product.categ_id.id if product else False,
                    }
                    waybill_line_vals_list.append(line_values)
                
                if waybill_line_vals_list:
                    waybill_line_obj.create(waybill_line_vals_list)
    
                _logger.info(f"New lines created for waybill {waybill_number}")

            return {'type': 'ir.actions.act_window_close'}

        except requests.exceptions.RequestException as e:
            _logger.error(f"Request failed: {e}")
            raise UserError(f"Request failed: {e}")

        except UserError as ue:
            _logger.error(f"Error processing waybills: {ue}")
            raise

        except Exception as e:
            _logger.error(f"Unexpected error: {e}")
            raise UserError(f"Unexpected error occurred: {e}")



