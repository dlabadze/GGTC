# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    inventory_request_id = fields.Many2one(
        'inventory.request',
        string='Inventory Request',
        index=True
    )

    inventory_request_ids = fields.One2many(
        'inventory.request',
        'mrp_production_id',
        string='Inventory Requests'
    )

    inventory_request_count = fields.Integer(
        string='Inventory Request Count',
        compute='_compute_inventory_request_count',
        store=False
    )
    inventory_request_number = fields.Char(
        string='Inventory Request Number',
        related="inventory_request_id.x_studio_request_number",
    )
    inventory_request_description = fields.Text(
        string='Inventory Request Description',
        related="inventory_request_id.description",
    )

    @api.depends('inventory_request_ids')
    def _compute_inventory_request_count(self):
        """Compute the number of inventory requests linked to this manufacturing order"""
        for record in self:
            record.inventory_request_count = len(record.inventory_request_ids)

    def action_view_inventory_request(self):
        """Open list view of inventory requests filtered by this manufacturing order"""
        self.ensure_one()
        
        # Get inventory requests linked to this manufacturing order
        inventory_requests = self.inventory_request_ids
        
        action = {
            'name': _('Inventory Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.request',
            'domain': [('mrp_production_id', '=', self.id)],
            'context': {
                'default_mrp_production_id': self.id,
                'search_default_mrp_production_id': self.id,
            },
            'target': 'current',
        }
        
        # If only one record, open in form view
        if len(inventory_requests) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': inventory_requests.id,
            })
        else:
            # Multiple or no records, open in list view (allows creation)
            action.update({
                'view_mode': 'list,form',
            })
        
        return action
