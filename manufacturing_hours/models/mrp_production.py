from odoo import models, fields


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    namushevari_saatebis_raodenoba = fields.Float(
        string='ნამუშევარი საათების რაოდენობა',
        digits=(16, 4),
        default=0.0,
    )

    tanxa = fields.Float(
        string="თანხა (ხელით ჩასაწერი)",
        digits=(16,2),
        default=0.0,
    )
    
