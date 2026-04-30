from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class GatvaliwinebuliRequestWizard(models.TransientModel):
    _name = 'gatvaliwinebuli.request.wizard'
    _description = 'Gatvaliwinebuli Request Wizard'

    source_request_id = fields.Many2one('inventory.request', string='Source Request')
    purchase_inventory_line_ids = fields.Many2many(
        'inventory.line',
        'gatvaliwinebuli_req_wizard_purchase_inv_rel',
        'wizard_id', 'line_id',
        string='Purchase Lines', help='Technical field to receive ids from context'
    )
    planned_inventory_line_ids = fields.Many2many(
        'inventory.line',
        'gatvaliwinebuli_req_wizard_planned_inv_rel',
        'wizard_id', 'line_id',
        string='Planned Lines', help='Technical field to receive ids from context'
    )
    purchase_line_ids = fields.One2many(
        'gatvaliwinebuli.request.wizard.line',
        'wizard_id',
        string='შესასყიდი',
        domain=[('line_type', '=', 'purchase')]
    )
    planned_line_ids = fields.One2many(
        'gatvaliwinebuli.request.wizard.line',
        'wizard_id',
        string='გათვალისწინებული',
        domain=[('line_type', '=', 'planned')]
    )
    purchase_total = fields.Float(string='შესასყიდი სულ', compute='_compute_totals')
    planned_total = fields.Float(string='გათვალისწინებული სულ', compute='_compute_totals')
    difference = fields.Float(string='სხვაობა', compute='_compute_totals')
    total_line_count = fields.Integer(string='Total Lines', compute='_compute_total_line_count')

    @api.depends('purchase_line_ids', 'planned_line_ids')
    def _compute_total_line_count(self):
        for wizard in self:
            wizard.total_line_count = len(wizard.purchase_line_ids) + len(wizard.planned_line_ids)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if 'default_purchase_inventory_line_ids' in ctx:
            val = ctx['default_purchase_inventory_line_ids']
            _logger.info(f'[default_get] purchase_ids={val}')
            purchase_lines = self.env['inventory.line'].sudo().browse(val)
            result = []
            for line in purchase_lines:
                result.append((0, 0, {
                    'request_number': line.request_id.x_studio_request_number,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'line_type': 'purchase',
                }))
            res['purchase_line_ids'] = result
        if 'default_planned_inventory_line_ids' in ctx:
            val = ctx['default_planned_inventory_line_ids']
            _logger.info(f'[default_get] planned_ids={val}')
            planned_lines = self.env['inventory.line'].sudo().browse(val)
            result = []
            for line in planned_lines:
                result.append((0, 0, {
                    'request_number': line.request_id.x_studio_request_number,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'line_type': 'planned',
                }))
            res['planned_line_ids'] = result
        return res

    @api.depends('purchase_line_ids.quantity', 'planned_line_ids.quantity')
    def _compute_totals(self):
        for wizard in self:
            purchase_total = sum(wizard.purchase_line_ids.mapped('quantity'))
            planned_total = sum(wizard.planned_line_ids.mapped('quantity'))
            wizard.purchase_total = purchase_total
            wizard.planned_total = planned_total
            wizard.difference = purchase_total - planned_total

    def action_ok(self):
        return {'type': 'ir.actions.act_window_close'}
