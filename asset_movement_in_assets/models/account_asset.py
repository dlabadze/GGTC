from odoo import models, fields

class AccountAsset(models.Model):
    _inherit = "account.asset"

    asset_movement_log_ids = fields.Many2many(
        'x_asset_movement_log',  # Related model
        'x_account_asset_x_asset_movement_log_rel',  # Same junction table
        'account_asset_id',  # Column for this model (account.asset)
        'x_asset_movement_log_id',  # Column for the other model
        string='Asset Movement Logs',
        help='All movement logs that include this asset'
    )

    # Optional: Add a count field
    movement_log_count = fields.Integer(
        compute='_compute_movement_log_count',
        string='Movement Log Count'
    )

    def _compute_movement_log_count(self):
        for asset in self:
            asset.movement_log_count = len(asset.asset_movement_log_ids)

