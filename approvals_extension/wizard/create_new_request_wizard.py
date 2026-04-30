from odoo import models, fields, api
from odoo.exceptions import UserError

class CreateNewRequestWizard(models.TransientModel):
    _name = 'create.new.request.wizard'
    _description = 'Create New Request Wizard'

    category_id = fields.Many2one("approval.category", string='Category', required=True)

    def create_approval_request(self):
        self.ensure_one()
        # Get the active approval request
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        
        if active_model == 'approval.request' and active_id:
            # Get the source request
            source_request = self.env['approval.request'].browse(active_id)
            
            # Create a new approval request based on the source
            new_request = source_request.copy(default={
                'category_id': self.category_id.id,
                'approver_ids': [(5, 0, 0)],
            })
            
            # Set the relationship
            new_request.request_from = source_request.id
            source_request.related_request_ids = [(4, new_request.id, 0)]
            
            # Copy attachments if the model supports them
            if hasattr(source_request, 'message_attachment_count') and source_request.message_attachment_count > 0:
                attachments = self.env['ir.attachment'].search([
                    ('res_model', '=', 'approval.request'),
                    ('res_id', '=', source_request.id),
                ])
                for attachment in attachments:
                    new_attachment = attachment.copy({
                        'res_model': 'approval.request',
                        'res_id': new_request.id,
                    })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Approval Request',
                'res_model': 'approval.request',
                'res_id': new_request.id,
                'view_mode': 'form',
                'target': 'current',
            }
