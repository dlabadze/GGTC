from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

# Try to safely inherit the Studio model
try:
    class AssetMovementLog(models.Model):
        _inherit = 'x_asset_movement_log'

        @api.onchange('x_studio_object_location_1')
        def _onchange_filter_locations(self):
            if self.x_studio_object_location_1:
                return {
                    'domain': {
                        'x_location_specific_1': [
                            ('x_studio_object_location_rel', '=', self.x_studio_object_location_1.id)
                        ]
                    }
                }
            else:
                return {
                    'domain': {
                        'x_location_specific_1': []
                    }
                }

        # available_specific_location_ids = fields.Many2many(
        #     'x_object_location',
        #     compute='_compute_available_specific_locations',
        #     string='Available Specific Locations',
        #     store=False
        # )

        # @api.depends('x_studio_object_location_1')
        # def _compute_available_specific_locations(self):
        #     for rec in self:
        #         if rec.x_studio_object_location_1:
        #             rec.available_specific_location_ids = self.env['x_location_specific'].search([
        #                 ('x_studio_object_location_rel', '=', rec.x_studio_object_location_1.id)
        #             ])
        #         else:
        #             rec.available_specific_location_ids = self.env['x_location_specific'].browse([])

except Exception as e:
    _logger.warning("Could not extend Studio model x_asset_movement_log: %s", e)