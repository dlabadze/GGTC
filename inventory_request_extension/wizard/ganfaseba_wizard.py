from lzma import FILTER_DELTA
from odoo import models, fields, api
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class GanfasebaWizard(models.TransientModel):
    _name = 'ganfaseba.wizard'
    _description = 'Ganfaseba Wizard'

    user_id = fields.Many2one('res.users', string='User')
    request_line_ids = fields.Many2many('inventory.line', string='Request Lines')



    def action_confirm(self):
        self.ensure_one()
        
        filtered_request_lines = self.request_line_ids.filtered(
            lambda line: line.request_id.stage_id.name in ['შესყ. დეპ. უფროსი', 'შესყ.დეპ. ჯგუფი'])
        if not filtered_request_lines:
            raise UserError(f'ვერ მოიძებნა მოთხოვნა "შესყ. დეპ. უფროსი" ან "შესყ.დეპ. ჯგუფი" სტეიჯში')
        requests = filtered_request_lines.mapped('request_id')
        lines = requests.mapped('line_ids')
        _logger.info(f"Lines: {lines}")
        stage = self.env['inventory.request.stage'].search([('name', '=', 'ბაზრის კვლევა და განფასება')], limit=1)
        lines.write({
            'ganawileba_user_id': self.user_id.id,
        })
        lines.request_id.stage_id = stage
        return {'type': 'ir.actions.act_window_close'}