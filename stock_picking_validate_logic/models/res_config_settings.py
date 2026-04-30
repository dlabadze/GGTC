from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nashti_control = fields.Boolean(
        string="Remainder Control",
        config_parameter='stock_picking_validate_logic.nashti_control'
    )