from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_assign(self, *args, **kwargs):

        if self.env.context.get('allow_ref_assign'):
            return super()._action_assign(*args, **kwargs)

        ref_moves = self.filtered(lambda m: m.picking_id.x_studio_request_ref)
        non_ref_moves = self - ref_moves

        result = None
        if non_ref_moves:
            result = super(StockMove, non_ref_moves)._action_assign(*args, **kwargs)

        if ref_moves:
            pass

        return result