from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SendSmsWizard(models.TransientModel):
    _name = 'send.sms.wizard'
    _description = 'Send SMS Wizard'

    config_id = fields.Many2one('sms.config', 'SMS Configuration', required=True, 
                               domain=[('active', '=', True)])
    to_number = fields.Char('To Number', required=True, 
                           help='Recipient phone number (e.g., +995595099666)')
    message = fields.Text('Message', required=True, 
                         help='SMS message content')


    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Get the first active configuration
        config = self.env['sms.config'].search([('active', '=', True)], limit=1)
        if config:
            res['config_id'] = config.id
        return res

    def action_send_sms(self):
        """Send the SMS message"""
        self.ensure_one()
        
        try:
            result = self.config_id.send_sms(
                to_number=self.to_number,
                message_text=self.message,
            )
            
            if result['success']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('SMS sent successfully to %s!') % self.to_number,
                        'type': 'success',
                    }
                }
            else:
                raise ValidationError(_('Failed to send SMS: %s') % result['response_text'])
                
        except Exception as e:
            raise ValidationError(_('Error sending SMS: %s') % str(e)) 