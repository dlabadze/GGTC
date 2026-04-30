from odoo import models, fields, api
from datetime import datetime
from calendar import monthrange
import logging

_logger = logging.getLogger(__name__)


class BulkInvoiceWizard(models.TransientModel):
    _name = 'bulk.invoice.wizard'
    _description = 'Bulk Invoice Generation Wizard'

    invoice_month = fields.Selection(
        selection=[
            ('1', 'January'),
            ('2', 'February'),
            ('3', 'March'),
            ('4', 'April'),
            ('5', 'May'),
            ('6', 'June'),
            ('7', 'July'),
            ('8', 'August'),
            ('9', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December'),
        ],
        string='Month',
        required=True,
        default=lambda self: str(fields.Date.today().month)
    )

    invoice_year = fields.Char(
        string='Year',
        required=True,
        default=lambda self: str(fields.Date.today().year),
        size=4
    )

    def action_generate_invoices(self):
        """Generate invoices for all subscriptions that need to be invoiced in selected month"""
        self.ensure_one()

        month = int(self.invoice_month)
        year = int(self.invoice_year)

        # Get first and last day of selected month
        first_day = fields.Date.from_string(f"{year}-{month:02d}-01")
        last_day_num = monthrange(year, month)[1]
        last_day = fields.Date.from_string(f"{year}-{month:02d}-{last_day_num:02d}")

        _logger.info(f"Generating invoices for month {month}/{year} (from {first_day} to {last_day})")

        # Find all active subscriptions that need invoicing in this month
        # A subscription needs invoicing if its next_invoice_date falls within or before the selected month
        subscriptions = self.env['sale.order'].search([
            ('is_subscription', '=', True),
            ('subscription_state', 'in', ['3_progress', '4_paused', '2_renewal']),
            ('next_invoice_date', '<=', last_day),  # Include past-due and current month
        ])

        _logger.info(f"Found {len(subscriptions)} subscriptions to invoice: {subscriptions.ids}")

        if not subscriptions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Subscriptions',
                    'message': f'No subscriptions found for invoicing in {month}/{year}',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        # Generate invoices for found subscriptions
        invoices_created = self.env['account.move']

        for subscription in subscriptions:
            try:
                # Check for draft invoices
                draft_invoices = subscription.invoice_ids.filtered(lambda am: am.state == 'draft')
                if draft_invoices:
                    _logger.warning(f"Subscription {subscription.name} has draft invoices, skipping")
                    continue

                # Check if subscription has any order lines
                if not subscription.order_line:
                    _logger.warning(f"Subscription {subscription.name} has no order lines, skipping")
                    continue

                _logger.info(
                    f"Subscription {subscription.name}: Found {len(subscription.order_line)} order lines: "
                    f"{subscription.order_line.mapped('product_id.name')}"
                )

                # Create invoice directly - if subscription is ready to invoice, just create it
                invoice = subscription._create_invoices(final=False)

                if invoice:
                    invoices_created |= invoice
                    _logger.info(f"Created invoice {invoice.mapped('name')} for subscription {subscription.name}")

                    # Update next invoice date
                    subscription._update_next_invoice_date()
            except Exception as e:
                _logger.error(f"Error creating invoice for subscription {subscription.name}: {str(e)}")
                import traceback
                _logger.error(traceback.format_exc())

        _logger.info(f"Successfully created {len(invoices_created)} invoices")

        # Show success message and open created invoices
        if invoices_created:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Created Invoices',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'domain': [('id', 'in', invoices_created.ids)],
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Invoices Created',
                    'message': 'No invoices were created. Please check logs for details.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
