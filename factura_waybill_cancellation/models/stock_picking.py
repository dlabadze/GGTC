from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import xml.etree.ElementTree as ET
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def cancel_waybill(self):
        """Cancel waybill from RS.GE (გაუქმება) and delete from combined invoice model"""
        for record in self:
            if not record.invoice_id:
                raise UserError(_('ზედნადები არ არის ატვირთული (invoice_id ცარიელია)'))
            
            if not record.rs_acc or not record.rs_pass:
                raise UserError(_('RS.GE ექაუნთი ან პაროლი არ არის მითითებული'))
            
            waybill_id = record.invoice_id
            rs_acc = record.rs_acc
            rs_pass = record.rs_pass
            
            _logger.info(f'Starting waybill cancellation (ref) for waybill_id: {waybill_id}')
            
            try:
                # Cancel waybill from RS.GE using ref_waybill method (გაუქმება)
                result = self.ref_waybill_from_rs(waybill_id, rs_acc, rs_pass)
                
                if result == 1:
                    _logger.info(f'✅ Successfully cancelled waybill {waybill_id} from RS.GE')
                elif result == 0:
                    # 0 might mean waybill is in "შენახული" (saved) status and cannot be cancelled
                    # Try using del_waybill instead for saved waybills
                    _logger.info(f'Waybill {waybill_id} returned 0 (possibly in შენახული status), trying del_waybill instead')
                    del_result = self.delete_waybill_from_rs(waybill_id, rs_acc, rs_pass)
                    if del_result == 1:
                        _logger.info(f'✅ Successfully deleted waybill {waybill_id} using del_waybill')
                    elif del_result == -101:
                        raise UserError(_('სხვისი ზედნადებია და ვერ წაშლით'))
                    elif del_result == -100:
                        raise UserError(_('სერვისის მომხმარებელი ან პაროლი არასწორია'))
                    elif del_result < 0:
                        error_text = self._get_error_text_from_code(rs_acc, rs_pass, del_result)
                        raise UserError(_(f'ზედნადების წაშლა ვერ მოხერხდა: {error_text}'))
                    else:
                        raise UserError(_(f'ზედნადების წაშლა ვერ მოხერხდა. კოდი: {del_result}'))
                elif result == -101:
                    raise UserError(_('სხვისი ზედნადებია და ვერ გააუქმებთ'))
                elif result == -100:
                    raise UserError(_('სერვისის მომხმარებელი ან პაროლი არასწორია'))
                elif result < 0:
                    # Get human-readable error message from RS.GE error codes API
                    error_text = self._get_error_text_from_code(rs_acc, rs_pass, result)
                    raise UserError(_(f'ზედნადების გაუქმება ვერ მოხერხდა: {error_text}'))
                else:
                    # Unknown positive result code - treat as success but log warning
                    _logger.warning(f'Unknown result code {result} for waybill {waybill_id}, treating as success')
                
                # Delete from combined invoice model
                if record.combined_invoice_id:
                    record.combined_invoice_id.unlink()
                    _logger.info(f'Deleted combined invoice record for waybill_id: {waybill_id}')
                
                # Clear all waybill-related fields (they are stored related fields)
                # Also clear completed_soap to allow re-upload
                record.write({
                    'invoice_id': False,
                    'invoice_number': False,
                    'combined_invoice_id': False,
                    'completed_soap': False,
                })
                
                _logger.info(f'✅ Successfully cancelled waybill {waybill_id}')
                
            except Exception as e:
                _logger.exception(f'Error cancelling waybill {waybill_id}')
                raise UserError(_(f'ზედნადების გაუქმება ვერ მოხერხდა: {str(e)}'))

    def delete_waybill_from_rs(self, waybill_id, rs_acc, rs_pass):
        """Delete waybill from RS.GE using del_waybill method
        
        Returns:
            1 - დასრულებულია (success)
            -1 - არა (failed)
            -101 - სხვისი ზედნადებია და ვერ წაშლით (not owner)
            -100 - სერვისის მომხმარებელი ან პაროლი არასწორია (auth error)
        """
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/del_waybill"
        }
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <del_waybill xmlns="http://tempuri.org/">
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                  <waybill_id>{waybill_id}</waybill_id>
                </del_waybill>
              </soap:Body>
            </soap:Envelope>"""
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"del_waybill({waybill_id})"
        )
        
        if not success:
            raise UserError(f"ზედნადების წაშლა ვერ მოხერხდა: {error_msg}")
        
        # Parse response to get result
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        result = self._parse_xml_response(response_text, './/ns:del_waybillResult', namespaces)
        
        if result is None:
            raise UserError("პასუხი ვერ მოიძებნა RS.GE-დან")
        
        try:
            result_code = int(result)
            return result_code
        except ValueError:
            raise UserError(f"არასწორი პასუხი RS.GE-დან: {result}")

    def ref_waybill_from_rs(self, waybill_id, rs_acc, rs_pass):
        """Cancel waybill from RS.GE using ref_waybill method (გაუქმება)
        
        Returns:
            1 - დასრულებულია (success)
            -1 - არა (failed)
            -101 - სხვისი ზედნადებია და ვერ გააუქმებთ (not owner)
            -100 - სერვისის მომხმარებელი ან პაროლი არასწორია (auth error)
        """
        url = "http://services.rs.ge/WayBillService/WayBillService.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/ref_waybill"
        }
        
        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <ref_waybill xmlns="http://tempuri.org/">
                  <su>{rs_acc}</su>
                  <sp>{rs_pass}</sp>
                  <waybill_id>{waybill_id}</waybill_id>
                </ref_waybill>
              </soap:Body>
            </soap:Envelope>"""
        
        success, response_text, error_msg = self._safe_soap_request(
            url, soap_request, headers, f"ref_waybill({waybill_id})"
        )
        
        if not success:
            raise UserError(f"ზედნადების გაუქმება ვერ მოხერხდა: {error_msg}")
        
        # Parse response to get result
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns': 'http://tempuri.org/'
        }
        
        result = self._parse_xml_response(response_text, './/ns:ref_waybillResult', namespaces)
        
        if result is None:
            raise UserError("პასუხი ვერ მოიძებნა RS.GE-დან")
        
        try:
            result_code = int(result)
            return result_code
        except ValueError:
            raise UserError(f"არასწორი პასუხი RS.GE-დან: {result}")

    def _safe_soap_request(self, url, soap_body, headers, service_name="API"):
        """
        Send SOAP request with comprehensive error handling
        These methods should be available from extension_views module
        If not available, we define them here as fallback
        """
        try:
            _logger.info(f'=== {service_name} REQUEST ===')
            _logger.info(f'URL: {url}')
            _logger.info(f'Body: {soap_body[:500]}...' if len(soap_body) > 500 else f'Body: {soap_body}')
            
            response = requests.post(
                url, 
                data=soap_body.encode('utf-8'), 
                headers=headers,
                timeout=60
            )
            
            _logger.info(f'{service_name} Response Status: {response.status_code}')
            _logger.info(f'{service_name} Response: {response.text[:500]}...' if len(response.text) > 500 else f'{service_name} Response: {response.text}')
            
            if response.status_code != 200:
                error_msg = f"HTTP შეცდომა {response.status_code}: {response.text[:200]}"
                return False, response.text, error_msg
            
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
        """Safely parse XML and extract element"""
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

