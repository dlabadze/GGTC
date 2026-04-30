from odoo import models, fields


class XAssetMovementLog(models.Model):
    _name = 'x_asset_movement_log'
    _description = 'Asset Movement Log'

    name = fields.Char(string='Description')
    line_ids = fields.One2many(
        'x.asset.movement.line', 'movement_id', string='Asset Lines'
    )
    # Add other fields as needed


class XAssetMovementLine(models.Model):
    _name = 'x.asset.movement.line'
    _description = 'Asset Movement Line'

    movement_id = fields.Many2one(
        'x_asset_movement_log', string='Movement Log', ondelete='cascade'
    )
    asset_id = fields.Many2one('gtc.asset', string='Asset')
