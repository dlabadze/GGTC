from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class BudgetSyncWizard(models.TransientModel):
    _name = 'budget.sync.wizard'
    _description = 'Budget Sync Wizard'

    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget Analytic',
        required=True,
        help='Select the budget analytic to sync amounts to'
    )

    def action_sync_budget(self):
        """Sync budget amounts from budgeting lines to budget analytic lines"""
        self.ensure_one()

        if not self.budget_analytic_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': 'Please select a Budget Analytic first.',
                }
            }

        # Get the current budgeting request from context
        budgeting_request_id = self.env.context.get('active_id')
        if not budgeting_request_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': 'No budgeting request found in context.',
                }
            }

        budgeting_request = self.env['budgeting.request'].browse(budgeting_request_id)
        if not budgeting_request.exists():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': 'Budgeting request not found.',
                }
            }

        try:
            # Get all budgeting lines from the current request
            budgeting_lines = budgeting_request.line_ids.filtered(lambda l: l.budget_name_main)

            if not budgeting_lines:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'message': 'No budgeting lines with analytic accounts found.',
                    }
                }

            # Group budgeting lines by analytic account
            account_totals = {}
            for line in budgeting_lines:
                account_id = line.budget_name_main.id
                if account_id not in account_totals:
                    account_totals[account_id] = {
                        'account': line.budget_name_main,
                        'total_amount': 0.0,
                        'line_count': 0
                    }

                # Get the single field value
                field_value = getattr(line, 'x_studio_float_field_4nk_1j1fvng8q', 0.0) or 0.0

                account_totals[account_id]['total_amount'] += field_value
                account_totals[account_id]['line_count'] += 1

            _logger.info(f"Found {len(account_totals)} unique analytic accounts to sync")

            # Find matching budget lines in the selected budget analytic
            budget_lines = self.env['budget.line'].search([
                ('budget_analytic_id', '=', self.budget_analytic_id.id)
            ])

            updated_count = 0
            created_count = 0

            # Update matching budget lines or create new ones
            for account_id, totals in account_totals.items():
                # Find budget line with matching account_id
                matching_budget_lines = budget_lines.filtered(lambda bl: bl.account_id.id == account_id)

                # Use the single field total
                total_amount = totals['total_amount']

                if matching_budget_lines:
                    # Update existing budget lines
                    for budget_line in matching_budget_lines:
                        try:
                            # Calculate remaining amounts based on budget_amount
                            pu_re_am = total_amount - (budget_line.pur_plan_am or 0.0)
                            co_re_am = total_amount - (budget_line.cont_am or 0.0)
                            pa_re_am = total_amount - (budget_line.paim_am or 0.0)

                            budget_line.write({
                                'budget_amount': total_amount,
                                'pu_re_am': pu_re_am,
                                'co_re_am': co_re_am,
                                'pa_re_am': pa_re_am,
                            })
                            updated_count += 1
                            _logger.info(f"Updated budget line {budget_line.id} for account {totals['account'].name} "
                                         f"with amount {total_amount} and calculated remaining amounts "
                                         f"from {totals['line_count']} budgeting lines")
                        except Exception as e:
                            _logger.error(f"Error updating budget line {budget_line.id}: {str(e)}")
                else:
                    # Create new budget line if no matching line found
                    try:
                        # For new lines, set remaining amounts equal to budget_amount (assuming other amounts are 0)
                        new_budget_line = self.env['budget.line'].create({
                            'budget_analytic_id': self.budget_analytic_id.id,
                            'account_id': account_id,
                            'budget_amount': total_amount,
                            'pu_re_am': total_amount,  # budget_amount - 0 (no pur_plan_am yet)
                            'co_re_am': total_amount,  # budget_amount - 0 (no cont_am yet)
                            'pa_re_am': total_amount,  # budget_amount - 0 (no paim_am yet)
                            # Add any other required fields here based on your budget.line model
                        })
                        created_count += 1
                        _logger.info(
                            f"Created new budget line {new_budget_line.id} for account {totals['account'].name} "
                            f"with amount {total_amount} and initial remaining amounts "
                            f"from {totals['line_count']} budgeting lines")
                    except Exception as e:
                        _logger.error(f"Error creating budget line for account {totals['account'].name}: {str(e)}")

            # Prepare result message
            messages = []
            if updated_count > 0:
                messages.append(f"Successfully updated {updated_count} budget line(s).")

            if created_count > 0:
                messages.append(f"Successfully created {created_count} new budget line(s).")

            message_type = 'success' if (updated_count > 0 or created_count > 0) else 'warning'
            message = ' '.join(messages) if messages else 'No updates or creations performed.'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': message_type,
                    'message': message,
                }
            }

        except Exception as e:
            _logger.error(f"Error in budget sync wizard: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': f'An error occurred during sync: {str(e)}',
                }
            }