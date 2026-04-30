from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)

class SmsConfig(models.Model):
    _name = 'sms.config'
    _description = 'SMS Service Configuration'
    _rec_name = 'name'

    name = fields.Char('Configuration Name', required=True, default='Default SMS Config')
    active = fields.Boolean('Active', default=True)
    
    # Service URL
    service_url = fields.Char('Service URL', required=True, 
                             default='http://10.10.53.60/magti/sms.asmx',
                             help='URL of the SMS service endpoint')
    
    # Authentication
    username = fields.Char('Username', required=True, default='gtc')
    password = fields.Char('Password', required=True, default='gtc4420')
    
    # Service Parameters
    client_id = fields.Integer('Client ID', required=True, default=367)
    service_id = fields.Integer('Service ID', required=True, default=4)
    userid = fields.Integer('User ID', required=True, default=-1)
    

    
    @api.constrains('service_url')
    def _check_service_url(self):
        for record in self:
            if record.service_url and not record.service_url.startswith(('http://', 'https://')):
                raise ValidationError(_('Service URL must start with http:// or https://'))
    
    def test_connection(self):
        """Test the SMS service connection"""
        self.ensure_one()
        
        try:
            # Prepare SOAP request
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <send_sms xmlns="http://tempuri.org/">
      <username>{self.username}</username>
      <password>{self.password}</password>
      <client_id>{self.client_id}</client_id>
      <service_id>{self.service_id}</service_id>
      <to>+995595099666</to>
      <text>Test SMS from Odoo</text>
      <userid>{self.userid}</userid>
    </send_sms>
  </soap:Body>
</soap:Envelope>"""
            
            # Send SOAP request
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://tempuri.org/send_sms'
            }
            
            response = requests.post(self.service_url, data=soap_body, headers=headers, timeout=30)
            
            # Parse SOAP response
            response_text = response.text
            sms_result = None
            
            try:
                if response.status_code == 200:
                    # Parse XML response to extract send_smsResult
                    root = ET.fromstring(response.text)
                    # Find the send_smsResult element
                    for elem in root.iter():
                        if 'send_smsResult' in elem.tag:
                            sms_result = elem.text
                            break
                    
                    # If we found a result, use it as response text
                    if sms_result:
                        response_text = sms_result
            except ET.ParseError:
                # If XML parsing fails, use the raw response
                pass
            
            if response.status_code == 200:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('SMS service connection test successful! Response: %s') % response_text,
                        'type': 'success',
                    }
                }
            else:
                raise ValidationError(_('Connection test failed. Status code: %s, Response: %s') % (response.status_code, response_text))
                
        except requests.exceptions.RequestException as e:
            raise ValidationError(_('Connection test failed: %s') % str(e))
        except Exception as e:
            raise ValidationError(_('Unexpected error: %s') % str(e))
    
    def send_sms(self, to_number, message_text):
        """Send SMS message"""
        self.ensure_one()
        
        if not to_number:
            raise ValidationError(_('Phone number is required'))
        
        if not message_text:
            raise ValidationError(_('Message text is required'))
        
        try:
            # Prepare SOAP request
            soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <send_sms xmlns="http://tempuri.org/">
      <username>{self.username}</username>
      <password>{self.password}</password>
      <client_id>{self.client_id}</client_id>
      <service_id>{self.service_id}</service_id>
      <to>{to_number}</to>
      <text>{message_text}</text>
      <userid>{self.userid}</userid>
    </send_sms>
  </soap:Body>
</soap:Envelope>"""
            
            # Send SOAP request
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://tempuri.org/send_sms'
            }
            
            response = requests.post(self.service_url, data=soap_body, headers=headers, timeout=30)
            
            # Parse SOAP response
            response_text = response.text
            sms_result = None
            
            try:
                if response.status_code == 200:
                    # Parse XML response to extract send_smsResult
                    root = ET.fromstring(response.text)
                    # Find the send_smsResult element
                    for elem in root.iter():
                        if 'send_smsResult' in elem.tag:
                            sms_result = elem.text
                            break
                    
                    # If we found a result, use it as response text
                    if sms_result:
                        response_text = sms_result
            except ET.ParseError:
                # If XML parsing fails, use the raw response
                pass
            
            # Log the response
            _logger.info('SMS sent to %s. Response: %s', to_number, response_text)
            
            # Create history record
            history_vals = {
                'config_id': self.id,
                'to_number': to_number,
                'message': message_text,
                'sender': self.username,
                'response_code': response.status_code,
                'response_text': response_text,
                'success': response.status_code == 200,
            }
            
            self.env['sms.history'].create(history_vals)
            
            return {
                'success': response.status_code == 200,
                'response_code': response.status_code,
                'response_text': response_text,
            }
            
        except requests.exceptions.RequestException as e:
            _logger.error('SMS sending failed: %s', str(e))
            raise ValidationError(_('SMS sending failed: %s') % str(e))
        except Exception as e:
            _logger.error('Unexpected error sending SMS: %s', str(e))
            raise ValidationError(_('Unexpected error: %s') % str(e)) 