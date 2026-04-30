from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class BudgetAnalytic(models.Model):
    _inherit = 'budget.analytic'

    # Mapping of revenue code names to their journal name(s)
    REVENUE_CODE_JOURNAL_MAP = {
        'შემოსავალი გგს მომსახურებიდან': ['გგს მომსახურება'],
        'შემოსავალი ტრანსპორტირებიდან': ['გაზის ტრანსპორტირება'],
        'შემოსავალი ტრანზიტიდან': ['შემოსავალი ტრანზიტი'],
        'სხვა შემოსავლები': ['საურავი', 'საურავი სხვა მომსახურებაზე', 'საურავი გგს'],
        'სხვა შემოსავლები გგს-ები მშენებლობა': ['ჟურნალი გგს მშენებლობა'],
    }

    def action_budget_confirm(self):
        """Override to calculate revenue amounts when confirming budget"""
        # Call the original method
        res = super(BudgetAnalytic, self).action_budget_confirm()

        # Calculate revenue amounts for lines with revenue budget type
        for budget in self:
            if budget.budget_type == 'revenue':
                budget._calculate_revenue_amounts()

        return res

    def _calculate_revenue_amounts(self):
        """Calculate revenue amounts from account.move and account.payment"""
        self.ensure_one()

        _logger.info(f"Calculating revenue amounts for budget {self.name}")

        # Get budget period
        date_from = self.date_from
        date_to = self.date_to

        # Process each budget line
        for line in self.budget_line_ids:
            # Check if x_plan2_id field exists and has a value
            if not hasattr(line, 'x_plan2_id') or not line.x_plan2_id:
                _logger.warning(f"Budget line {line.id} does not have x_plan2_id set, skipping")
                continue

            revenue_code = line.x_plan2_id
            _logger.info(f"Processing budget line {line.id} with revenue code: {revenue_code.name}")

            # Calculate accrued amount from account.move (invoices)
            accrued_amount = self._calculate_accrued_from_moves(
                date_from, date_to, revenue_code
            )

            # Calculate paid amount from account.payment
            paid_amount = self._calculate_paid_from_payments(
                date_from, date_to, revenue_code
            )

            # Special case: for revenue codes in the journal map,
            # set contract_amount_revenue to the accrued amount
            contract_amount = 0.0
            if revenue_code.name in self.REVENUE_CODE_JOURNAL_MAP:
                contract_amount = accrued_amount
                _logger.info(f"Special case detected: {revenue_code.name}, setting contract_amount_revenue to {contract_amount}")

            # Update budget line with calculated amounts
            line.write({
                'accrued_amount_revenue': accrued_amount,
                'paid_amount_revenue': paid_amount,
                'contract_amount_revenue': contract_amount,
            })

            _logger.info(
                f"Updated line {line.id}: accrued={accrued_amount}, "
                f"paid={paid_amount}, contract={contract_amount}"
            )

    def _calculate_accrued_from_moves(self, date_from, date_to, revenue_code):
        """Calculate total amount from account.move records"""
        journal_names = self.REVENUE_CODE_JOURNAL_MAP.get(revenue_code.name)

        if journal_names:
            # Special case: filter by journal name(s)
            _logger.info(f"Special case: filtering by journal name(s) {journal_names} for revenue code '{revenue_code.name}'")
            journals = self.env['account.journal'].search([
                ('name', 'in', journal_names)
            ])

            if not journals:
                _logger.warning(f"No journals found with names {journal_names}")
                return 0.0

            # Search for account moves (invoices) matching criteria by journal(s)
            moves = self.env['account.move'].search([
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
                ('journal_id', 'in', journals.ids),
                ('state', '=', 'posted'),  # Only posted invoices
            ])
        else:
            # Normal case: filter by revenue_code
            moves = self.env['account.move'].search([
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
                ('revenue_code', '=', revenue_code.id),
                ('state', '=', 'posted'),  # Only posted invoices
            ])

        # Calculate total amount
        total = 0.0
        for move in moves:
            
            total += move.amount_total

        _logger.info(
            f"Found {len(moves)} invoice(s) for revenue code {revenue_code.name}, "
            f"total amount: {total}"
        )

        return total

    def _calculate_paid_from_payments(self, date_from, date_to, revenue_code):
        """Calculate total amount from account.payment records"""
        # Search for payments matching criteria
        payments = self.env['account.payment'].search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('revenue_code', '=', revenue_code.id),
            ('state', '=', 'paid'),  # Only posted payments
        ])

        # Calculate total amount
        total = sum(payments.mapped('amount'))

        _logger.info(
            f"Found {len(payments)} payment(s) for revenue code {revenue_code.name}, "
            f"total amount: {total}"
        )

        return total
