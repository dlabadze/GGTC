from odoo import models, fields, api


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment')


    def action_open_equipment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Equipment',
            'res_model': 'maintenance.equipment',
            'view_mode': 'form',
            'res_id': self.equipment_id.id,
        }