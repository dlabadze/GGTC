from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class SmsHistory(models.Model):
    _name = 'sms.history'
    _description = 'SMS History'
    _order = 'create_date desc'
    _rec_name = 'to_number'

    config_id = fields.Many2one('sms.config', 'SMS Configuration', required=True, ondelete='cascade')
    to_number = fields.Char('To Number', required=True, help='Recipient phone number')
    message = fields.Text('Message', required=True, help='SMS message content')
    sender = fields.Char('Sender', help='Sender name or number')
    
    # Response tracking
    response_code = fields.Integer('Response Code', help='HTTP response code from SMS service')
    response_text = fields.Text('Response Text', help='Full response from SMS service')
    success = fields.Boolean('Success', help='Whether the SMS was sent successfully')
    
    # Additional fields
    create_date = fields.Datetime('Sent Date', readonly=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Sent By', readonly=True)
    
    # Computed fields
    status_display = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending')
    ], string='Status', compute='_compute_status', store=True)
    
    @api.depends('success', 'response_code')
    def _compute_status(self):
        for record in self:
            if record.success and record.response_code == 200:
                record.status_display = 'success'
            elif record.response_code:
                record.status_display = 'failed'
            else:
                record.status_display = 'pending'
    
    def resend_sms(self):
        """Resend the SMS message"""
        self.ensure_one()
        
        try:
            result = self.config_id.send_sms(
                to_number=self.to_number,
                message_text=self.message,
                sender=self.sender
            )
            
            if result['success']:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('SMS resent successfully!'),
                        'type': 'success',
                    }
                }
            else:
                raise ValidationError(_('Failed to resend SMS: %s') % result['response_text'])
                
        except Exception as e:
            raise ValidationError(_('Error resending SMS: %s') % str(e))
    
    def view_response(self):
        """View the full response from SMS service"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS Response'),
            'res_model': 'sms.history',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_response_text': self.response_text},
        } 