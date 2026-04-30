import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    _TARGET_STAGE_NAME = 'შესყ. დეპ. უფროსი'

    purchase_plan_id = fields.Many2one('purchase.plan', string='Purchase Plan')
    cpv_code_id = fields.Many2one(
        'purchase.plan.line',
        string='CPV Code',
        domain="[('plan_id', '=', purchase_plan_id)]",
    )
    budget_analytic_id = fields.Many2one('budget.analytic', string='Budget Analytic')
    budget_analytic_line_id = fields.Many2one(
        'budget.line',
        string='Budget Analytic Line',
        domain="[('budget_analytic_id', '=', budget_analytic_id)]",
    )
    budget_account_id = fields.Many2one('account.analytic.account', string='Budget Account', related='budget_analytic_line_id.account_id')

    def _sync_purchase_plan_to_request_lines(self, request, purchase_plan_id, purchase_plan_line_id):
        """Sync request header plan/cpv to purchase inventory lines.

        For each inventory line where x_studio_purchase == True:
        - set x_studio_purchase_plan to purchase_plan_id
        - set x_studio_purchase_plan_line to purchase_plan_line_id
        """
        if not purchase_plan_id and not purchase_plan_line_id:
            return

        if not request or not request.line_ids:
            return

        # Only update lines that are marked as purchase lines.
        purchase_lines = request.line_ids.filtered(lambda l: getattr(l, 'x_studio_purchase', False))
        if not purchase_lines:
            return

        # Avoid unnecessary writes.
        lines_to_update = purchase_lines.filtered(
            lambda l: (not l.x_studio_purchase_plan or l.x_studio_purchase_plan.id != purchase_plan_id)
            or (not l.x_studio_purchase_plan_line or l.x_studio_purchase_plan_line.id != purchase_plan_line_id)
        )
        if not lines_to_update:
            return

        lines_to_update.write({
            'x_studio_purchase_plan': purchase_plan_id,
            'x_studio_purchase_plan_line': purchase_plan_line_id,
        })

    def _update_purchase_plan_reservation_filtered(self, purchase_plan_id, purchase_plan_line_id):
        """Update purchase plan line reservation using filtered inventory lines.

        Filter rules (per request requirements):
        - inventory.line.x_studio_purchase == True
        - inventory.line.x_studio_purchase_plan == purchase_plan_id
        - inventory.line.x_studio_purchase_plan_line == purchase_plan_line_id
        """
        if not purchase_plan_id and not purchase_plan_line_id:
            return

        purchase_plan_line = self.env['purchase.plan.line'].browse(purchase_plan_line_id)
        if not purchase_plan_line.exists():
            return

        inventory_lines = self.env['inventory.line'].search([
            ('x_studio_purchase', '=', True),
            ('x_studio_purchase_plan', '=', purchase_plan_id),
            ('x_studio_purchase_plan_line', '=', purchase_plan_line_id),
        ])

        total_amount = sum(inventory_lines.mapped('amount')) if inventory_lines else 0.0
        remaining_resource = (getattr(purchase_plan_line, 'pu_ac_am', 0.0) or 0.0) - total_amount

        # These fields are used by existing inventory.line reservation logic.
        if not (hasattr(purchase_plan_line, 'x_studio_reserved') and hasattr(purchase_plan_line, 'x_studio_remaining_resource')):
            _logger.debug(
                "Skipping purchase plan line reservation update (missing expected fields) for %s",
                purchase_plan_line_id,
            )
            return

        purchase_plan_line.with_context(disable_purchase_plan_update=True).write({
            'x_studio_reserved': total_amount,
            'x_studio_remaining_resource': remaining_resource,
        })

    def action_purchase_plan(self):
        """Manual action to sync plan/CPV to request lines and recompute reservation.

        This replaces the previous automatic `create()`/`write()` behavior.
        """
        for record in self:
            stages = [record._TARGET_STAGE_NAME, 'CPV კოდები']
            if record.stage_id and record.stage_id.name not in stages:
                continue

            purchase_plan_id = record.purchase_plan_id.id if record.purchase_plan_id else False
            cpv_code_id = record.cpv_code_id.id if record.cpv_code_id else False

            record._sync_purchase_plan_to_request_lines(record, purchase_plan_id, cpv_code_id)
            record._update_purchase_plan_reservation_filtered(purchase_plan_id, cpv_code_id)

        return True

    def action_update_budget_fields(self):
        """Copy header budget fields to all request lines."""
        line_model = self.env['inventory.line']
        can_write_budget_analytic = 'budget_analytic' in line_model._fields
        can_write_budget_analytic_line = 'budget_analytic_line' in line_model._fields

        for record in self:
            if not record.line_ids:
                continue

            vals = {}
            if can_write_budget_analytic:
                vals['budget_analytic'] = record.budget_analytic_id.id or False
            if can_write_budget_analytic_line:
                vals['budget_analytic_line'] = record.budget_analytic_line_id.id or False

            if vals:
                record.line_ids.write(vals)

        return True