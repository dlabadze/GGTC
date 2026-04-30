from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    partner_id = fields.Many2one('res.partner', compute='_compute_partner_id', store=True)

    @api.depends('invoice_line_ids','invoice_line_ids.partner_id')
    def _compute_partner_id(self):
        _logger.info(f"Computing partner_id for {self}")
        for rec in self:
            partners = rec.line_ids.mapped('partner_id')
            if partners:
                rec.partner_id = partners[0]
            else:
                rec.partner_id = False