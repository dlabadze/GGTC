from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import xml.etree.ElementTree as ET
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    # These methods should be available from extension_views module
    # If not available, we'll define them here

    def cancel_factura(self):
        """Cancel/Delete factura from RS.GE (status -1) and delete from combined invoice model"""
        for record in self:
            if not record.factura_num:
                raise UserError(_('ფაქტურა არ არის ატვირთული (factura_num ცარიელია)'))
            
            if not record.rs_acc or not record.rs_pass:
                raise UserError(_('RS.GE ექაუნთი ან პაროლი არ არის მითითებული'))
            
            factura_num = record.factura_num
            rs_acc = record.rs_acc
            rs_pass = record.rs_pass
            
            _logger.info(f'Starting factura cancellation (ref) for factura_num: {factura_num}')
            
            try:
                # Get user_id
                user_id = self.chek(rs_acc, rs_pass)
                
                # Try to cancel factura using ref_invoice_status (უარყოფა) first
                try:
                    self.ref_invoice_status_from_rs(factura_num, user_id, rs_acc, rs_pass)
                except UserError as ref_error:
                    # If ref_invoice_status fails (e.g., factura is in შენახული status),
                    # fall back to change_invoice_status with status -1 (deleted)
                    _logger.info(f'ref_invoice_status failed, trying change_invoice_status with status -1: {ref_error}')
                    self.change_invoice_status_to_deleted(factura_num, user_id, rs_acc, rs_pass)
                
                # Delete from combined invoice model
                if record.combined_invoice_id:
                    record.combined_invoice_id.unlink()
                    _logger.info(f'Deleted combined invoice record for factura_num: {factura_num}')
                
                # Clear all factura-related fields (they are stored related fields)
                # Also clear completed_soap to allow re-upload
                record.write({
                    'factura_num': False,
                    'get_invoice_id': False,
                    'combined_invoice_id': False,
                    'completed_soap': False,
                })
                
                _logger.info(f'✅ Successfully cancelled factura {factura_num}')
                
            except Exception as e:
                _logger.exception(f'Error cancelling factura {factura_num}')
                raise UserError(_(f'ფაქტურის გაუქმება ვერ მოხერხდა: {str(e)}'))

    def get_invoice_desc_items(self, factura_num, user_id, rs_acc, rs_pass):
        """Get invoice line items from RS.GE"""
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/get_invoice_desc"
        }
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <get_invoice_desc xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <invois_id>{factura_num}</invois_id>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </get_invoice_desc>
              </soap:Body>
            </soap:Envelope>"""
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"get_invoice_desc({factura_num})"
        )
        
        if not success:
            raise UserError(f"ფაქტურის მონაცემების მიღება ვერ მოხერხდა: {error_msg}")
        
        # Parse response to get line items
        line_items = []
        try:
            root = ET.fromstring(response_text)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ns': 'http://tempuri.org/'
            }
            
            # Find all line items in the response
            for item in root.findall('.//ns:id', namespaces):
                item_id = item.text
                if item_id:
                    line_items.append({'id': item_id})
            
            # Alternative parsing if response structure is different
            if not line_items:
                # Try to find in DataTable format
                for item in root.findall('.//id', namespaces):
                    item_id = item.text
                    if item_id:
                        line_items.append({'id': item_id})
            
            _logger.info(f'Found {len(line_items)} line items to delete')
            
        except Exception as e:
            _logger.warning(f'Could not parse line items from response: {e}')
            # Continue even if we can't parse line items - the invoice status change will still work
        
        return line_items

    def delete_invoice_desc_item(self, user_id, item_id, invois_id, rs_acc, rs_pass):
        """Delete a single invoice line item from RS.GE"""
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/delete_invoice_desc"
        }
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <delete_invoice_desc xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <id>{item_id}</id>
                  <inv_id>{invois_id}</inv_id>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </delete_invoice_desc>
              </soap:Body>
            </soap:Envelope>"""
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"delete_invoice_desc(item_id:{item_id})"
        )
        
        if not success:
            _logger.warning(f'Failed to delete invoice desc item {item_id}: {error_msg}')
            # Continue with other items
        else:
            _logger.info(f'✅ Deleted invoice desc item {item_id}')

    def ref_invoice_status_from_rs(self, factura_num, user_id, rs_acc, rs_pass, ref_text="გაუქმება"):
        """Cancel/Refuse factura using ref_invoice_status (უარყოფა) in RS.GE"""
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/ref_invoice_status"
        }
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <ref_invoice_status xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <inv_id>{factura_num}</inv_id>
                  <ref_text>{ref_text}</ref_text>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </ref_invoice_status>
              </soap:Body>
            </soap:Envelope>"""
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"ref_invoice_status({factura_num})"
        )
        
        if not success:
            raise UserError(f"ფაქტურის უარყოფა ვერ მოხერხდა: {error_msg}")
        
        # Check response
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        result = self._parse_xml_response(response_text, './/ns:ref_invoice_statusResult', namespaces)
        
        # ref_invoice_status returns bool, so check for false or error
        if result and (result.lower() == 'false' or result.startswith('-')):
            # Get human-readable error message from RS.GE error codes API
            error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
            raise UserError(f"ფაქტურის უარყოფა ვერ მოხერხდა: {error_text}")
        
        _logger.info(f'✅ Invoice refused/cancelled (ref_invoice_status) for factura_num: {factura_num}')
        return True

    def change_invoice_status_to_deleted(self, factura_num, user_id, rs_acc, rs_pass):
        """Change invoice status to -1 (deleted) in RS.GE - fallback method"""
        url = "http://www.revenue.mof.ge/ntosservice/ntosservice.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/change_invoice_status"
        }
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <change_invoice_status xmlns="http://tempuri.org/">
                  <user_id>{user_id}</user_id>
                  <inv_id>{factura_num}</inv_id>
                  <status>-1</status>
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                </change_invoice_status>
              </soap:Body>
            </soap:Envelope>"""
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"change_invoice_status({factura_num}, status:-1)"
        )
        
        if not success:
            raise UserError(f"ფაქტურის სტატუსის შეცვლა ვერ მოხერხდა: {error_msg}")
        
        # Check response
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        result = self._parse_xml_response(response_text, './/ns:change_invoice_statusResult', namespaces)
        
        if result and result.startswith('-'):
            # Get human-readable error message from RS.GE error codes API
            error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
            raise UserError(f"ფაქტურის სტატუსის შეცვლა ვერ მოხერხდა: {error_text}")
        
        _logger.info(f'✅ Invoice status changed to deleted (-1) for factura_num: {factura_num}')
        return True

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
                "http://services.rs.ge/WayBillService/WayBillService.asmx",
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

    def cancel_waybill(self):
        """Cancel/Delete waybill - placeholder for future implementation"""
        for record in self:
            if not record.invoice_id:
                raise UserError(_('Waybill ID არ არის მითითებული (invoice_id ცარიელია)'))
            
            # TODO: Implement waybill cancellation when RS.GE API details are available
            raise UserError(_('Waybill cancellation not yet implemented'))
