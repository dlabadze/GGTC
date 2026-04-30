from odoo import models, fields, api, _


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'


    def action_return_button(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Return Button',
            'res_model': 'return.button.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_stage_sequence': self.stage_id.sequence,
                'default_request_id': self.id,
            },
        }