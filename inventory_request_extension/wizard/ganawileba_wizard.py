from odoo import models, fields, api


class GanawilebaWizard(models.TransientModel):
    _name = 'ganawileba.wizard'
    _description = 'Ganawileba User Selection Wizard'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self._default_user_id()
    )
    request_id = fields.Many2one(
        'inventory.request',
        string='Inventory Request',
        required=True
    )

    @api.model
    def _default_user_id(self):
        """Default to requested_by from request_id or current user"""
        if self.env.context.get('default_request_id'):
            request = self.env['inventory.request'].browse(self.env.context['default_request_id'])
            if request.exists() and request.requested_by:
                return request.requested_by.id
        return self.env.user.id

    def action_confirm(self):
        """Execute the ganawileba logic with selected user"""
        self.ensure_one()
        request = self.request_id
        
        if request.line_ids:
            ganawileba_lines = request.line_ids.filtered(lambda line: line.is_ganawileba == True)
            if ganawileba_lines:
                ganawileba_lines.write({
                    'is_ganawileba': False,
                    'ganawileba_user_id': self.user_id.id
                })
            else:
                request.line_ids.write({
                    'is_ganawileba': False,
                    'ganawileba_user_id': self.user_id.id
                })
        
        return {'type': 'ir.actions.act_window_close'}

