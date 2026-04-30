from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    gatvaliwinebuli_lines = fields.Many2many(
        'inventory.line',
        'inventory_request_line_gatvaliswinebuli_rel',
        'request_id',
        'line_id',
        string="Gatvaliswinebuli Lines",
    )
    relative_inventory_request_ids = fields.Many2many(
        'inventory.request',
        'inventory_request_gatvaliswinebuli_rel',
        'request_id',
        'relative_request_id',
        string="Relative Inventory Requests",
    )

    def _get_gatvaliwinebuli_requests(self, exclude_request_id=None, department_id=None):
        """Get related requests for gatvaliwinebuli, excluding rejected stage."""
        stage = self.env['inventory.request.stage'].search(
            [('name', '=', 'სასაწყობე მეურ. სამმ.')], limit=1
        )
        stage_rejected = self.env['inventory.request.stage'].search(
            [('name', '=', 'უარყოფილი')], limit=1
        )
        if not stage or not department_id:
            return self.env['inventory.request']

        domain = [
            ('department_id', '=', department_id.id),
            # ('x_studio_selection_field_6ca_1j76p9boc', '=', 'მარაგები'),
        ]
        if exclude_request_id:
            domain.append(('id', '!=', exclude_request_id))
        if stage_rejected:
            domain.append(('stage_id', '!=', stage_rejected.id))

        requests = self.env['inventory.request'].search(domain)
        return requests.filtered(lambda x: x.stage_id and x.stage_id.sequence > stage.sequence)

    def action_open_gatvaliwinebuli_wizard(self):
        stage = self.env['inventory.request.stage'].search(
            [('name', '=', 'სასაწყობე მეურ. სამმ.')], limit=1
        )
        purchase_lines = self.env['inventory.line']
        planned_lines = self.env['inventory.line']
        # if stage and self.stage_id.id == stage.id and self.department_id:
        requests = self._get_gatvaliwinebuli_requests(
            exclude_request_id=self.id,
            department_id=self.department_id
        )
        product_ids = self.line_ids.mapped('product_id').ids
        all_lines = requests.mapped('line_ids').filtered(
            lambda l: l.product_id and l.product_id.id in product_ids
        )
        purchase_lines = all_lines.filtered(lambda l: l.x_studio_purchase and\
                l.request_id.x_studio_selection_field_6ca_1j76p9boc == 'მარაგები')
        planned_lines = all_lines.filtered(lambda l: l.x_studio_boolean_field_2bu_1j82g13ub)
        _logger.info(
            f'[action_open_gatvaliwinebuli_wizard] request={self.id} '
            f'purchase_lines={purchase_lines.ids} planned_lines={planned_lines.ids}'
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'მოთხოვნის ლაინები',
            'res_model': 'gatvaliwinebuli.request.wizard',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                'default_source_request_id': self.id,
                'default_purchase_inventory_line_ids': purchase_lines.ids,
                'default_planned_inventory_line_ids': planned_lines.ids,
            }
        }


class InventoryLine(models.Model):
    _inherit = 'inventory.line'

    def action_set_purchase(self):
        _logger.info(f'========[action_set_purchase]=======================')
        user = self.env.user
        if user.name in ['ირაკლი ოთარაშვილი', 'ალექსანდრე კოპაძე', 'AdminUser', 'ადმინისტრატორი', 'ადმინი']:
            self.with_context(skip_gatvaliwinebuli_check=True).write({'x_studio_purchase': True})
            stage = self.env['inventory.request.stage'].search(
                [('name', '=', 'სასაწყობე მეურ. სამმ.')], limit=1
            )
            _logger.info(
                f'[action_set_purchase] line={self.id} product={self.product_id.name} '
                f'stage={stage.id if stage else None} request_stage={self.request_id.stage_id.id}'
            )
            if not stage or self.request_id.stage_id.id != stage.id:
                _logger.info('[action_set_purchase] stage mismatch - no wizard')
                return False
            if not self.request_id.department_id:
                return False

            requests = self.request_id._get_gatvaliwinebuli_requests(
                exclude_request_id=self.request_id.id,
                department_id=self.request_id.department_id
            )
            _logger.info(f'[action_set_purchase] requests={requests.ids}')
            all_lines = requests.mapped('line_ids').filtered(
                lambda l: l.product_id and l.product_id.id == self.product_id.id
            )
            purchase_lines = all_lines.filtered(lambda l: l.x_studio_purchase and\
                        l.request_id.x_studio_selection_field_6ca_1j76p9boc == 'მარაგები')
            _logger.info(f'[action_set_purchase] purchase_lines={purchase_lines.ids}')
            planned_lines = all_lines.filtered(lambda l: l.x_studio_boolean_field_2bu_1j82g13ub)
            _logger.info(f'[action_set_purchase] planned_lines={planned_lines.ids}')
            _logger.info(
                f'[action_set_purchase] purchase_lines={purchase_lines.ids} '
                f'planned_lines={planned_lines.ids}'
            )
            if purchase_lines or planned_lines:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'მოთხოვნის ლაინები',
                    'res_model': 'gatvaliwinebuli.wizard',
                    'view_mode': 'form',
                    'views': [[False, 'form']],
                    'target': 'new',
                    'context': {
                        'default_source_request_id': self.request_id.id,
                        'default_source_line_id': self.id,
                        'default_purchase_inventory_line_ids':purchase_lines.ids,
                        'default_planned_inventory_line_ids': planned_lines.ids,
                    }
                }
            self.request_id.gatvaliwinebuli_lines = [(6, 0, [])]
            self.request_id.relative_inventory_request_ids = [(5, 0, 0)]
            return False
