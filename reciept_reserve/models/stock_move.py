from odoo import fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    for_reserve = fields.Boolean(
        string='რეზერვისთვის',
        default=False,
        copy=True,
    )
