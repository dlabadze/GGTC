from odoo import models, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.depends('name', 'location_id', 'location_id.complete_name')
    def _compute_complete_name(self):
        """Override to ensure display_name is computed correctly"""
        return super()._compute_complete_name()

    def name_get(self):
        """Override name_get to use display_name for better visibility in dropdowns"""
        result = []
        for location in self:
            # Use display_name which includes the full path
            result.append((location.id, location.display_name))
        return result
