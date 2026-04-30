# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PurchaseRequisitionPaymentWizard(models.TransientModel):
    _name = 'purchase.requisition.payment.wizard'
    _description = 'Purchase Requisition Payment Selection Wizard'

    st_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Statement Line',
        required=True,
        readonly=True
    )

    transaction_amount = fields.Monetary(
        string='Transaction Amount',
        related='st_line_id.amount',
        currency_field='currency_id',
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='st_line_id.currency_id',
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        related='st_line_id.partner_id',
        readonly=True
    )

    purchase_requisition_ids = fields.Many2many(
        'purchase.requisition',
        compute='_compute_purchase_requisition_ids',
        string='Available Purchase Requisitions'
    )

    purchase_requisition_id = fields.Many2one(
        'purchase.requisition',
        string='Purchase Requisition',
        required=True,
        help='Select the purchase requisition to update the paid amount',
        domain="[('id', 'in', purchase_requisition_ids)]"
    )

    current_paid_amount = fields.Float(
        string='Current Paid Amount',
        compute='_compute_current_paid_amount',
        readonly=True,
        digits=(16, 2)
    )

    new_paid_amount = fields.Float(
        string='New Paid Amount',
        compute='_compute_new_paid_amount',
        readonly=True,
        digits=(16, 2)
    )

    @api.depends('st_line_id', 'st_line_id.partner_id')
    def _compute_purchase_requisition_ids(self):
        """Compute available purchase requisitions based on partner"""
        for wizard in self:
            if wizard.partner_id:
                # Search for purchase requisitions with matching vendor
                requisitions = self.env['purchase.requisition'].search([
                    ('vendor_id', '=', wizard.partner_id.id)
                ])
                wizard.purchase_requisition_ids = requisitions
            else:
                # If no partner, show all purchase requisitions
                wizard.purchase_requisition_ids = self.env['purchase.requisition'].search([])

    @api.depends('purchase_requisition_id', 'purchase_requisition_id.paid_amount')
    def _compute_current_paid_amount(self):
        """Get current paid amount from selected purchase requisition"""
        for wizard in self:
            if wizard.purchase_requisition_id and hasattr(wizard.purchase_requisition_id, 'paid_amount'):
                wizard.current_paid_amount = wizard.purchase_requisition_id.paid_amount or 0.0
            else:
                wizard.current_paid_amount = 0.0

    @api.depends('current_paid_amount', 'transaction_amount')
    def _compute_new_paid_amount(self):
        """Calculate the new paid amount by adding transaction amount to current paid amount"""
        for wizard in self:
            wizard.new_paid_amount = wizard.current_paid_amount + abs(wizard.transaction_amount or 0.0)

    def action_confirm(self):
        """Update the purchase requisition paid_amount and remaining_amount"""
        self.ensure_one()

        if not self.purchase_requisition_id:
            raise UserError('Please select a Purchase Requisition.')

        # Calculate remaining amount
        contract_amount = self.purchase_requisition_id.contract_amount or 0.0
        remaining_amount = contract_amount - self.new_paid_amount

        # Update the paid_amount and remaining_amount fields
        self.purchase_requisition_id.write({
            'paid_amount': self.new_paid_amount,
            'remaining_amount': remaining_amount
        })

        _logger.info(
            'Updated purchase.requisition %s: paid_amount from %s to %s, remaining_amount to %s (transaction: %s)',
            self.purchase_requisition_id.id,
            self.current_paid_amount,
            self.new_paid_amount,
            remaining_amount,
            self.transaction_amount
        )

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cancel the wizard without updating"""
        return {'type': 'ir.actions.act_window_close'}
