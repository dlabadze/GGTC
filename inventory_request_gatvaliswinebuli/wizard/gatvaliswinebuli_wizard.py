from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

class GatvaliwinebuliWizard(models.TransientModel):
    _name = 'gatvaliwinebuli.wizard'
    _description = 'Gatvaliwinebuli Wizard'

    source_request_id = fields.Many2one('inventory.request', string='Source Request')
    source_line_id = fields.Many2one('inventory.line', string='Source Line')
    purchase_inventory_line_ids = fields.Many2many(
        'inventory.line',
        'gatvaliwinebuli_wizard_purchase_inv_rel',
        'wizard_id', 'line_id',
        string='Purchase Lines', help='Technical field to receive ids from context'
    )
    planned_inventory_line_ids = fields.Many2many(
        'inventory.line',
        'gatvaliwinebuli_wizard_planned_inv_rel',
        'wizard_id', 'line_id',
        string='Planned Lines', help='Technical field to receive ids from context'
    )
    purchase_line_ids = fields.One2many(
        'gatvaliwinebuli.wizard.line',
        'wizard_id',
        string='შესასყიდი',
        domain=[('line_type', '=', 'purchase')]
    )
    planned_line_ids = fields.One2many(
        'gatvaliwinebuli.wizard.line',
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

    def _extract_ids_from_context(self, val):
        """Extract flat list of integer ids from context value (handles [1,2,3] or [(6,0,[1,2,3])])."""
        if not val:
            return []
        if isinstance(val, (list, tuple)):
            if len(val) == 3 and val[0] == 6:
                inner = val[2]
                return [int(x) for x in inner if isinstance(x, int)] if isinstance(inner, (list, tuple)) else []
            if val and isinstance(val[0], (list, tuple)) and len(val[0]) == 3 and val[0][0] == 6:
                inner = val[0][2]
                return [int(x) for x in inner if isinstance(x, int)] if isinstance(inner, (list, tuple)) else []
            return [int(x) for x in val if isinstance(x, int)]
        return []

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
                    'source_inventory_line_id': line.id,
                    'wizard_id': self.id,
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
                    'source_inventory_line_id': line.id,
                    'wizard_id': self.id,
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
        if self.source_line_id:
            self.source_line_id.with_context(skip_gatvaliwinebuli_check=True).write({
                'x_studio_purchase': False,
                'x_studio_boolean_field_2bu_1j82g13ub': True,
            })
        inventory_lines = self.env['inventory.line']
        for line in self.purchase_line_ids:
            if line.source_inventory_line_id:
                inventory_lines |= line.source_inventory_line_id
        for line in self.planned_line_ids:
            if line.source_inventory_line_id:
                inventory_lines |= line.source_inventory_line_id
        # for line in inventory_lines:
        #     line.with_context(skip_gatvaliwinebuli_check=True).write({
        #         'x_studio_purchase': False,
        #         'x_studio_boolean_field_2bu_1j82g13ub': True,
        #     })
        self.source_line_id.x_studio_purchase = False
        self.source_line_id.x_studio_boolean_field_2bu_1j82g13ub = True
        if self.source_request_id and inventory_lines:
            self.source_request_id.gatvaliwinebuli_lines |= inventory_lines
            self.source_request_id.relative_inventory_request_ids |= inventory_lines.mapped('request_id')
        return {'type': 'ir.actions.act_window_close'}
