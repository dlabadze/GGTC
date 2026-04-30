from odoo import models, fields, api


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    account_asset_ids = fields.One2many('account.asset', 'equipment_id', string='Account Assets')
    stock_picking_ids = fields.One2many('stock.picking', 'equipment_id', string='Stock Pickings')
    picking_count = fields.Integer(compute='_compute_picking_count')
    # lokacia_konk = fields.Many2one('x_location_specific', string='ლოკაცია კონკ')
    # obieqti_lokacia = fields.Many2one('x_object_location', string='ობიექტი ლოკაცია')

    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.stock_picking_ids)

    def action_open_stock_pickings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Pickings',
            'res_model': 'stock.picking',
            'view_mode': 'list',
            'domain': [('equipment_id', '=', self.id)],
            'context': {
                'default_equipment_id': self.id,
                'create': False,
            },
        }

    def action_open_account_assets(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Account Assets',
            'res_model': 'account.asset',
            'view_mode': 'list',
            'domain': [('equipment_id', '=', self.id)],
            'context': {
                'default_equipment_id': self.id,
                'no_create': True,
            },
        }