from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from calendar import monthrange
import logging

_logger = logging.getLogger(__name__)

SUBSCRIPTION_PROGRESS_STATE = ['3_progress', '4_paused']


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Remove the constraint that next_invoice_date must be after start_date
    # This allows us to set date_start_sub in previous months
    _sql_constraints = [
        ('check_start_date_lower_next_invoice_date', 'CHECK(1=1)',
         'Constraint removed to allow flexible date handling'),
    ]

    # New fields for subscription start and end dates
    date_start_sub = fields.Date(
        string='Subscription Start Date',
        help='Actual start date for subscription billing. Used for first invoice proration.'
    )
    date_end_sub = fields.Date(
        string='Subscription End Date',
        help='Actual end date for subscription. Used for final invoice proration when closing.'
    )

    def _process_auto_invoice(self, invoice):
        """Override to keep invoices as draft - remove the invoice.action_post() call"""
        # Original code was: invoice.action_post()
        # We do nothing here to keep invoice as draft
        return

    def _recurring_invoice_get_subscriptions(self, grouped=False, batch_size=30):
        _logger.info("=== _recurring_invoice_get_subscriptions START ===")
        _logger.info(f"Today: {fields.Date.today()}, grouped={grouped}, batch_size={batch_size}")

        need_cron_trigger = False
        limit = False

        if self:
            domain = [('id', 'in', self.ids), ('subscription_state', 'in', SUBSCRIPTION_PROGRESS_STATE)]
            batch_size = False
        else:
            domain = self._recurring_invoice_domain()
            limit = batch_size and batch_size + 1

        _logger.info(f"Domain: {domain}")

        if grouped:
            all_subscriptions = self.read_group(
                domain,
                ['id:array_agg'],
                self._get_auto_invoice_grouping_keys(),
                limit=limit, lazy=False)
            all_subscriptions = [self.browse(res['id']) for res in all_subscriptions]
            need_cron_trigger = batch_size and len(all_subscriptions) > batch_size
            all_subscriptions = [subscription._get_subscriptions_to_invoice() for subscription in all_subscriptions]
        else:
            all_subscriptions = self.search(domain, limit=limit)
            _logger.info(f"Found {len(all_subscriptions)} subscriptions: {all_subscriptions.ids}")

            # Log details for each
            for sub in all_subscriptions:
                _logger.info(f"Sub {sub.id}: next_invoice={sub.next_invoice_date}, is_batch={sub.is_batch}, "
                             f"payment_exception={sub.payment_exception}, lines={len(sub.order_line)}")

            all_subscriptions = all_subscriptions._get_subscriptions_to_invoice()
            need_cron_trigger = batch_size and len(all_subscriptions) > batch_size

        if batch_size:
            all_subscriptions = all_subscriptions[:batch_size]

        _logger.info(
            f"RESULT: {len(all_subscriptions)} subscriptions to invoice: {all_subscriptions.ids if not isinstance(all_subscriptions, list) else [s.ids for s in all_subscriptions]}")
        _logger.info("=== _recurring_invoice_get_subscriptions END ===")

        return all_subscriptions, need_cron_trigger

    def _get_end_of_month(self, date):
        """
        Get the last day of the month for a given date.
        """
        if not date:
            return date

        last_day = monthrange(date.year, date.month)[1]
        return date.replace(day=last_day)

    def _update_next_invoice_date(self):
        """
        Override to set next invoice date to end of month for monthly billing.
        """
        for order in self:
            if not order.is_subscription:
                continue

            last_invoice_date = order.next_invoice_date or order.start_date
            if not last_invoice_date:
                continue

            if order.plan_id and order.plan_id.billing_period_unit == 'month':
                # For monthly billing: add months and set to end of target month
                target_date = last_invoice_date + relativedelta(months=order.plan_id.billing_period_value)
                new_date = self._get_end_of_month(target_date)
                order.next_invoice_date = new_date
                _logger.info(
                    "Monthly subscription %s: updated next_invoice_date from %s to %s (end of month)",
                    order.name, last_invoice_date, new_date
                )
            elif order.plan_id:
                # For other billing periods: use original logic
                order.next_invoice_date = last_invoice_date + order.plan_id.billing_period
                _logger.info(
                    "Non-monthly subscription %s: updated next_invoice_date from %s to %s",
                    order.name, last_invoice_date, order.next_invoice_date
                )

            order.last_reminder_date = False

    def write(self, vals):
        """
        Override write to catch any direct updates to next_invoice_date and apply end-of-month logic.
        Also handle date_start_sub and date_end_sub to automatically adjust next_invoice_date.
        """
        result = super().write(vals)

        # If date_start_sub is set, adjust next_invoice_date to end of that month
        if 'date_start_sub' in vals:
            for order in self:
                if (order.is_subscription and order.plan_id and
                        order.plan_id.billing_period_unit == 'month' and
                        order.date_start_sub and
                        not self.env.context.get('skip_end_month_adjustment')):

                    # Set next_invoice_date to end of the month of date_start_sub
                    end_of_month_date = self._get_end_of_month(order.date_start_sub)
                    _logger.info(
                        "Subscription %s: date_start_sub set to %s, adjusting next_invoice_date to %s (end of month)",
                        order.name, order.date_start_sub, end_of_month_date
                    )
                    order.with_context(skip_end_month_adjustment=True).next_invoice_date = end_of_month_date

        # If date_end_sub is set, adjust next_invoice_date to that date
        if 'date_end_sub' in vals:
            for order in self:
                if (order.is_subscription and order.plan_id and
                        order.plan_id.billing_period_unit == 'month' and
                        order.date_end_sub and
                        not self.env.context.get('skip_end_month_adjustment')):

                    # Set next_invoice_date to date_end_sub for final invoice
                    _logger.info(
                        "Subscription %s: date_end_sub set to %s, adjusting next_invoice_date to %s",
                        order.name, order.date_end_sub, order.date_end_sub
                    )
                    order.with_context(skip_end_month_adjustment=True).next_invoice_date = order.date_end_sub

        # If next_invoice_date was updated and this is a monthly subscription
        if 'next_invoice_date' in vals:
            for order in self:
                if (order.is_subscription and order.plan_id and
                        order.plan_id.billing_period_unit == 'month' and
                        order.next_invoice_date and
                        not self.env.context.get('skip_end_month_adjustment')):

                    # Apply end-of-month adjustment
                    original_date = order.next_invoice_date
                    end_of_month_date = self._get_end_of_month(original_date)

                    if original_date != end_of_month_date:
                        _logger.info(
                            "Adjusting monthly subscription %s next_invoice_date from %s to %s (end of month)",
                            order.name, original_date, end_of_month_date
                        )
                        # Use context to avoid infinite recursion
                        order.with_context(skip_end_month_adjustment=True).next_invoice_date = end_of_month_date

        return result

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()

        # Original logic: Set journal from template
        if self.sale_order_template_id.journal_id:
            vals['journal_id'] = self.sale_order_template_id.journal_id.id

        # New logic: Set invoice date for subscription invoices
        if self.is_subscription:
            invoice_date = None

            # CASE 1: First invoice with early start - use end of next_invoice_date month
            if self.date_start_sub and self._is_first_invoice():
                # Use end of month from next_invoice_date
                if self.next_invoice_date:
                    invoice_date = self._get_end_of_month(self.next_invoice_date)
                else:
                    invoice_date = self._get_end_of_month(fields.Date.today())
                _logger.info(
                    f"Subscription {self.name}: First invoice with early start - "
                    f"setting invoice_date to {invoice_date} (end of month)"
                )

            # CASE 2: Final invoice with early end - use date_end_sub (exact date)
            elif self.date_end_sub and (self.subscription_state == '6_churn' or self.env.context.get('is_final_invoice')):
                invoice_date = self.date_end_sub
                _logger.info(
                    f"Subscription {self.name}: Final invoice with early end - "
                    f"setting invoice_date to {invoice_date} (exact date)"
                )

            # CASE 3: Regular invoice - use end of next_invoice_date month
            else:
                if self.next_invoice_date:
                    invoice_date = self._get_end_of_month(self.next_invoice_date)
                else:
                    invoice_date = self._get_end_of_month(fields.Date.today())
                _logger.info(
                    f"Subscription {self.name}: Regular invoice - "
                    f"setting invoice_date to {invoice_date} (end of next_invoice_date month)"
                )

            vals['invoice_date'] = invoice_date
            vals['is_subscription_invoice'] = True

        return vals

    def _is_first_invoice(self):
        """
        Check if this is the first invoice for the subscription.
        Returns True if no invoices have been created yet.
        """
        self.ensure_one()

        # Check if there are any invoices linked to this subscription
        invoice_count = self.env['account.move'].search_count([
            ('invoice_origin', '=', self.name),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '!=', 'cancel')
        ])

        return invoice_count == 0

    def _get_proration_info(self):
        """
        Calculate proration information for this subscription.
        Enhanced to handle both early start (first invoice) and early end (final invoice).

        Returns: (period_start, period_end, days_in_month, actual_days, needs_proration, is_final_invoice)
        """
        self.ensure_one()

        if not self.is_subscription or not self.plan_id or self.plan_id.billing_period_unit != 'month':
            return None, None, None, None, False, False

        today = fields.Date.today()
        is_final_invoice = False

        # Determine the current billing period based on invoice creation date
        from calendar import monthrange
        current_month_end = today.replace(day=monthrange(today.year, today.month)[1])

        # CASE 1: First invoice with early start (date_start_sub is filled and no previous invoices)
        if self.date_start_sub and self._is_first_invoice():
            period_start = self.date_start_sub
            period_end = self.next_invoice_date or current_month_end

            _logger.info(
                f"Subscription {self.name}: FIRST INVOICE with early start - "
                f"using date_start_sub={period_start}, period_end={period_end}"
            )

        # CASE 2: Final invoice with early end (date_end_sub is filled and closing)
        elif self.date_end_sub and (self.subscription_state == '6_churn' or self.env.context.get('is_final_invoice')):
            # For final invoice, always bill from the first day of date_end_sub's month
            # This ensures we only bill for the partial month, not from the previous month
            period_start = self.date_end_sub.replace(day=1)
            period_end = self.date_end_sub
            is_final_invoice = True

            _logger.info(
                f"Subscription {self.name}: FINAL INVOICE with early end - "
                f"period_start={period_start}, period_end={period_end}, last_invoice_date={self.last_invoice_date}"
            )

        # CASE 3: Regular billing period (after first invoice)
        else:
            # For regular invoices after first invoice, bill for full month
            # Use first day of next_invoice_date month to last day of next_invoice_date month
            if not self._is_first_invoice() and self.next_invoice_date:
                # This is a regular invoice (not first, not final)
                # Bill for the full month of next_invoice_date
                period_start = self.next_invoice_date.replace(day=1)
                period_end = self._get_end_of_month(self.next_invoice_date)

                _logger.info(
                    f"Subscription {self.name}: REGULAR FULL MONTH INVOICE - "
                    f"period_start={period_start}, period_end={period_end}, next_invoice_date={self.next_invoice_date}"
                )
            else:
                # First invoice or fallback
                # If we have next_invoice_date, use full month of that date
                if self.next_invoice_date:
                    period_start = self.next_invoice_date.replace(day=1)
                    period_end = self._get_end_of_month(self.next_invoice_date)

                    _logger.info(
                        f"Subscription {self.name}: FALLBACK FULL MONTH INVOICE - "
                        f"period_start={period_start}, period_end={period_end}, next_invoice_date={self.next_invoice_date}"
                    )
                else:
                    # Last resort: use start_date
                    period_start = self.start_date
                    period_end = current_month_end

                    _logger.info(
                        f"Subscription {self.name}: LAST RESORT INVOICE - "
                        f"period_start={period_start}, period_end={period_end}"
                    )

        if not period_start or not period_end:
            return None, None, None, None, False, False

        # Calculate the billing month (use period_end's month)
        days_in_billing_month = monthrange(period_end.year, period_end.month)[1]
        actual_days = (period_end - period_start).days + 1

        needs_proration = actual_days < days_in_billing_month

        _logger.info(
            f"Subscription {self.name}: Proration check - period {period_start} to {period_end}, "
            f"{actual_days}/{days_in_billing_month} days, needs_proration={needs_proration}, "
            f"is_final={is_final_invoice}, "
            f"last_invoice_date={self.last_invoice_date}, date_start_sub={self.date_start_sub}, "
            f"is_first_invoice={self._is_first_invoice()}"
        )

        return period_start, period_end, days_in_billing_month, actual_days, needs_proration, is_final_invoice

    def action_close_subscription(self):
        """
        Create final prorated invoice when closing subscription with date_end_sub.
        This is called before the actual close to generate the last invoice.
        Does NOT change subscription state - that's handled by parent set_close().
        """
        for order in self:
            if not order.is_subscription:
                continue

            # If date_end_sub is set, create final prorated invoice
            if order.date_end_sub:
                _logger.info(
                    f"Closing subscription {order.name} with end date {order.date_end_sub}. "
                    f"Creating final prorated invoice."
                )

                try:
                    # Create the final invoice with context flag to trigger final invoice logic
                    invoice = order.with_context(is_final_invoice=True)._create_invoices()
                    if invoice:
                        _logger.info(
                            f"Created final prorated invoice {invoice.name} for subscription {order.name}"
                        )
                    else:
                        _logger.warning(
                            f"No invoice created for subscription {order.name} with end date {order.date_end_sub}"
                        )
                except Exception as e:
                    _logger.error(
                        f"Error creating final invoice for subscription {order.name}: {str(e)}"
                    )
                    raise

        return True

    def set_close(self, close_reason_id=False, renew=False):
        """
        Override the standard close method to handle final prorated invoice.
        """
        # First create final invoice if needed
        self.action_close_subscription()

        # Call parent method with proper parameters
        return super().set_close(close_reason_id=close_reason_id, renew=renew)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _prepare_invoice_line(self, **optional_values):
        """
        Override to apply prorated amount for subscription lines
        """
        res = super()._prepare_invoice_line(**optional_values)

        # Check if this line's order needs proration
        if self.order_id.is_subscription:
            period_start, period_end, days_in_month, actual_days, needs_proration, is_final = \
                self.order_id._get_proration_info()

            if needs_proration and days_in_month and actual_days:
                # Calculate prorated price_subtotal (the actual amount to charge)
                original_price = self.price_unit
                prorated_price = (original_price / days_in_month) * actual_days
                prorated_subtotal = prorated_price * self.product_uom_qty

                # Store the prorated subtotal as a custom field
                res['price_subtotal_override'] = prorated_subtotal

                invoice_type = "FINAL" if is_final else "FIRST" if self.order_id._is_first_invoice() else "REGULAR"

                _logger.info(
                    f"Sale Order Line {self.id} ({self.product_id.name}) [{invoice_type} INVOICE]: "
                    f"Setting price_subtotal_override={prorated_subtotal:.2f} "
                    f"(original={original_price:.2f}, prorated={prorated_price:.2f}, "
                    f"qty={self.product_uom_qty}, billing {actual_days}/{days_in_month} days)"
                )

        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_subscription_invoice = fields.Boolean(
        string='Is Subscription Invoice',
        default=False,
        help='Flag to indicate this invoice was created from a subscription with proration'
    )

    def _prepare_product_base_line_for_taxes_computation(self, product_line):
        """
        Override to use prorated price for subscription invoices
        """
        # Check if this is a subscription invoice with override
        if self.is_subscription_invoice and product_line.price_subtotal_override:
            # Calculate the effective price_unit that would give us the prorated subtotal
            quantity = product_line.quantity if product_line.quantity else 1.0
            discount_factor = (1 - product_line.discount / 100) if product_line.discount else 1.0

            if quantity and discount_factor:
                effective_price_unit = product_line.price_subtotal_override / (quantity * discount_factor)
            else:
                effective_price_unit = product_line.price_subtotal_override

            _logger.info(
                f"AccountMove {self.name}: Overriding price_unit for line {product_line.id}: "
                f"original={product_line.price_unit:.2f}, effective={effective_price_unit:.2f}, "
                f"override_subtotal={product_line.price_subtotal_override:.2f}"
            )

            # Call the parent method but with modified price_unit
            self.ensure_one()
            is_invoice = self.is_invoice(include_receipts=True)
            sign = self.direction_sign if is_invoice else 1
            rate = self.invoice_currency_rate if is_invoice else (
                abs(product_line.amount_currency) / abs(product_line.balance) if product_line.balance else 0.0
            )

            return self.env['account.tax']._prepare_base_line_for_taxes_computation(
                product_line,
                price_unit=effective_price_unit,
                quantity=quantity,
                discount=product_line.discount if is_invoice else 0.0,
                rate=rate,
                sign=sign,
                special_mode=False if is_invoice else 'total_excluded',
            )
        else:
            # Use standard calculation
            return super()._prepare_product_base_line_for_taxes_computation(product_line)

    def action_post(self):
        """
        Override action_post to ensure due dates are adjusted for weekends/holidays before posting
        """
        # Filter only moves that need due date adjustment
        moves_to_adjust = self.filtered(
            lambda m: m.invoice_date_due and self._is_weekend_or_holiday(m.invoice_date_due)
        )

        if moves_to_adjust:
            _logger.info(f"Found {len(moves_to_adjust)} moves with due dates on weekends/holidays")

            for move in moves_to_adjust:
                original_due_date = move.invoice_date_due
                adjusted_due_date = self._ensure_business_due_date(move)

                _logger.info(
                    f"Move {move.name}: Adjusting due date from {original_due_date} "
                    f"to {adjusted_due_date} before posting"
                )
                move.invoice_date_due = adjusted_due_date

        # Call the original action_post method
        return super().action_post()

    def _ensure_business_due_date(self, move):
        """
        Ensure the due date is a business day (not weekend or holiday)
        """
        if not move.invoice_date_due:
            return move.invoice_date_due

        due_date = move.invoice_date_due
        original_due_date = due_date

        # Adjust if due date falls on weekend or holiday
        while self._is_weekend_or_holiday(due_date):
            _logger.debug(f"Due date {due_date.strftime('%A %Y-%m-%d')} is weekend/holiday, moving to next day")
            due_date += timedelta(days=1)

        if due_date != original_due_date:
            _logger.info(f"Adjusted due date from {original_due_date} to {due_date} (next business day)")

        return due_date

    def _get_business_due_date(self, start_date, days_to_add):
        """
        Calculate due date by adding calendar days, then adjusting if final date
        falls on weekend or holiday
        """
        if days_to_add <= 0:
            return start_date

        # Step 1: Add the calendar days
        due_date = start_date + timedelta(days=days_to_add)

        _logger.info(f"Calculating due date: {start_date} + {days_to_add} calendar days = {due_date}")

        # Step 2: If due date falls on weekend or holiday, move to next business day
        original_due_date = due_date
        while self._is_weekend_or_holiday(due_date):
            _logger.debug(f"Due date {due_date.strftime('%A %Y-%m-%d')} is weekend/holiday, moving to next day")
            due_date += timedelta(days=1)

        if due_date != original_due_date:
            _logger.info(f"Adjusted due date from {original_due_date} to {due_date} (next business day)")

        return due_date

    def _is_weekend_or_holiday(self, date):
        """
        Check if date is weekend or holiday
        """
        # Check weekend (Saturday=5, Sunday=6)
        if date.weekday() >= 5:
            return True

        # Check holiday from resource.calendar.leaves
        return self._is_holiday(date)

    def _is_holiday(self, date):
        """
        Check if a date is a public holiday using resource.calendar.leaves
        """
        try:
            # Handle different date types
            if isinstance(date, datetime):
                check_datetime = date
                check_date = date.date()
            elif hasattr(date, 'year'):
                check_date = date
                check_datetime = datetime.combine(date, datetime.min.time())
            else:
                check_date = fields.Date.from_string(date)
                check_datetime = datetime.combine(check_date, datetime.min.time())

            # Search for public holidays
            domain = [
                ('date_from', '<=', check_datetime),
                ('date_to', '>=', check_datetime),
                ('resource_id', '=', False),
            ]

            if 'holiday' in self.env['resource.calendar.leaves']._fields:
                domain.append(('holiday', '=', True))

            holidays = self.env['resource.calendar.leaves'].search(domain)

            if holidays:
                return True

            # Additional check for calendar holidays
            domain_calendar = [
                ('date_from', '<=', check_datetime),
                ('date_to', '>=', check_datetime),
                ('calendar_id', '!=', False),
                ('resource_id', '=', False),
            ]

            calendar_holidays = self.env['resource.calendar.leaves'].search(domain_calendar)
            if calendar_holidays:
                return True

            return self._is_basic_holiday(check_date)

        except Exception as e:
            _logger.warning(f"Error checking holiday for date {date}: {str(e)}")
            try:
                fallback_date = date if hasattr(date, 'month') else fields.Date.from_string(str(date))
                return self._is_basic_holiday(fallback_date)
            except:
                return False

    def _is_basic_holiday(self, date):
        """
        Fallback method for basic holiday checking
        """
        basic_holidays = [
            (1, 1),  # New Year's Day
            (12, 25),  # Christmas Day
            (12, 24),  # Christmas Eve
        ]
        return (date.month, date.day) in basic_holidays

    @api.depends('needed_terms')
    def _compute_invoice_date_due(self):
        """
        Override the original due date computation to use business days
        """
        today = fields.Date.context_today(self)
        for move in self:
            if move.needed_terms:
                max_due_date = max(
                    (k['date_maturity'] for k in move.needed_terms.keys() if k),
                    default=False,
                )

                if max_due_date and move.invoice_payment_term_id and move.invoice_date:
                    needs_due_date_adjustment = any(
                        line.nb_days > 0 for line in move.invoice_payment_term_id.line_ids
                    )

                    if needs_due_date_adjustment:
                        business_due_dates = []

                        for line in move.invoice_payment_term_id.line_ids:
                            if line.nb_days > 0:
                                business_date = self._get_business_due_date(move.invoice_date, line.nb_days)
                                business_due_dates.append(business_date)
                            else:
                                regular_date = move.invoice_date + timedelta(days=line.nb_days)
                                business_due_dates.append(regular_date)

                        if business_due_dates:
                            move.invoice_date_due = max(business_due_dates)
                        else:
                            move.invoice_date_due = max_due_date
                    else:
                        move.invoice_date_due = max_due_date
                else:
                    move.invoice_date_due = max_due_date
            else:
                move.invoice_date_due = move.invoice_date_due or today


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_subtotal_override = fields.Monetary(
        string='Subtotal Override',
        help='Override subtotal for subscription proration',
        currency_field='currency_id',
        store=True
    )