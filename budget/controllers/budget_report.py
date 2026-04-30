from odoo import http
from odoo.http import request
import json


class BudgetReportController(http.Controller):

    @http.route('/budget/purchase_plan_lines_report', type='http', auth='user', website=True)
    def purchase_plan_lines_report(self, **kwargs):
        """Purchase Plan Lines report page with sums and selection"""
        purchase_plans = request.env['purchase.plan'].search([])
        return request.render('budget.purchase_plan_lines_report_template', {
            'purchase_plans': purchase_plans,
        })

    @http.route('/budget/get_plan_lines', type='json', auth='user')
    def get_plan_lines(self, purchase_plan_id):
        """Get all purchase plan lines, optionally filtered by plan"""
        if purchase_plan_id == 'all':
            plan_lines = request.env['purchase.plan.line'].search([])
        elif purchase_plan_id:
            plan_lines = request.env['purchase.plan.line'].search([
                ('plan_id', '=', int(purchase_plan_id))
            ])
        else:
            return []

        def get_selection_label(record, field_name):
            val = getattr(record, field_name, False)
            if not val:
                return ''
            field_obj = record._fields.get(field_name)
            if field_obj and hasattr(field_obj, 'selection'):
                return dict(field_obj.selection).get(val, val)
            return val

        result = []
        for line in plan_lines:
            result.append({
                'id': line.id,
                'plan_name': line.plan_id.name if line.plan_id else '',
                'cpv_code': line.cpv_id.code if line.cpv_id else '',
                'cpv_name': line.cpv_name or '',
                'funding_source': get_selection_label(line, 'funding_source'),
                'purchase_method': line.purchase_method_id.name if line.purchase_method_id else '',
                'purchase_reason': line.purchase_reason_id.name if line.purchase_reason_id else '',
                'vadebi': get_selection_label(line, 'vadebi'),
                'pu_st_am': line.pu_st_am or 0,
                'pu_ac_am': line.pu_ac_am or 0,
                'pu_diff': line.pu_diff or 0,
                'pcon_am': line.pcon_am or 0,
                'pc_re_am': line.pc_re_am or 0,
                'paim_am': line.paim_am or 0,
                'pa_re_am': line.pa_re_am or 0,
                'budget_lines_allocated': line.budget_lines_allocated or 0,
                'remaining_to_allocate': line.remaining_to_allocate or 0,
                'currency_symbol': line.currency_id.symbol if line.currency_id else '',
            })
        return result

    @http.route('/budget/visual_report', type='http', auth='user', website=True)
    def budget_visual_report(self, **kwargs):
        """Main visual report page"""
        purchase_plans = request.env['purchase.plan'].search([])

        return request.render('budget.visual_report_template', {
            'purchase_plans': purchase_plans,
        })

    @http.route('/budget/get_budget_cpvs', type='json', auth='user')
    def get_budget_cpvs(self, purchase_plan_id):
        """Get unique analytic accounts from CPV lines connected to the selected purchase plan"""
        try:
            if not purchase_plan_id:
                return []

            # Get purchase plan lines for this plan
            plan_lines = request.env['purchase.plan.line'].search([
                ('plan_id', '=', int(purchase_plan_id))
            ])

            # Get budget CPVs that are referenced in these plan lines
            budget_cpvs_from_plan = plan_lines.mapped('budget_cpv_id').filtered(lambda x: x)

            if not budget_cpvs_from_plan:
                return []

            # Get all CPV lines from these budget CPVs
            cpv_lines = request.env['budget.cpv.line'].search([
                ('budget_cpv_id', 'in', budget_cpvs_from_plan.ids)
            ])

            # Get unique analytic accounts from budget lines
            budget_lines = cpv_lines.mapped('budget_line_id').filtered(lambda x: x)
            analytic_accounts = set()

            for budget_line in budget_lines:
                # Check if budget line has account_id (analytic account)
                if hasattr(budget_line, 'account_id') and budget_line.account_id:
                    analytic_accounts.add(budget_line.account_id)
                else:
                    # Check for x_plan fields if account_id is not available
                    for field_name in budget_line._fields:
                        if field_name.startswith('x_plan'):
                            plan = getattr(budget_line, field_name, False)
                            if plan and hasattr(plan, 'id'):
                                analytic_accounts.add(plan)
                                break

            # Convert to list and prepare result
            result = []
            for account in analytic_accounts:
                display_name = account.name or f'Account {account.id}'
                if hasattr(account, 'code') and account.code:
                    display_name = f"{account.code} - {display_name}"

                result.append({
                    'id': account.id,
                    'name': display_name,
                    'code': account.code if hasattr(account, 'code') else '',
                })

            # Sort by name for better UX
            result.sort(key=lambda x: x['name'])

            return result
        except Exception as e:
            return {'error': str(e)}

    @http.route('/budget/get_chart_data', type='json', auth='user')
    def get_chart_data(self, purchase_plan_id, budget_cpv_id):
        """Get data for charts filtered by analytic account from budget lines"""
        try:
            if not purchase_plan_id or not budget_cpv_id:
                return {}

            # budget_cpv_id is now actually an analytic account ID
            analytic_account_id = int(budget_cpv_id)

            # Get purchase plan lines for this plan
            purchase_plan_lines = request.env['purchase.plan.line'].search([
                ('plan_id', '=', int(purchase_plan_id))
            ])

            if not purchase_plan_lines:
                return {'error': 'No purchase plan lines found for this plan'}

            # Get budget CPVs from purchase plan lines
            budget_cpvs = purchase_plan_lines.mapped('budget_cpv_id').filtered(lambda x: x)

            if not budget_cpvs:
                return {'error': 'No budget CPVs found in purchase plan lines'}

            # Find budget CPV lines that belong to the selected analytic account
            cpv_lines = request.env['budget.cpv.line'].search([
                ('budget_cpv_id', 'in', budget_cpvs.ids)
            ])

            # Filter CPV lines by analytic account
            filtered_cpv_lines = []
            for cpv_line in cpv_lines:
                budget_line = cpv_line.budget_line_id
                if budget_line:
                    # Check account_id first
                    if hasattr(budget_line,
                               'account_id') and budget_line.account_id and budget_line.account_id.id == analytic_account_id:
                        filtered_cpv_lines.append(cpv_line)
                    else:
                        # Check x_plan fields
                        for field_name in budget_line._fields:
                            if field_name.startswith('x_plan'):
                                plan = getattr(budget_line, field_name, False)
                                if plan and hasattr(plan, 'id') and plan.id == analytic_account_id:
                                    filtered_cpv_lines.append(cpv_line)
                                    break

            if not filtered_cpv_lines:
                return {'error': 'No budget lines found for the selected analytic account'}

            # Get the analytic account for display
            analytic_account = request.env['account.analytic.account'].browse(analytic_account_id)
            if not analytic_account.exists():
                # Try to find it in other models if it's an x_plan field
                analytic_account = None
                for cpv_line in filtered_cpv_lines:
                    budget_line = cpv_line.budget_line_id
                    for field_name in budget_line._fields:
                        if field_name.startswith('x_plan'):
                            plan = getattr(budget_line, field_name, False)
                            if plan and hasattr(plan, 'id') and plan.id == analytic_account_id:
                                analytic_account = plan
                                break
                    if analytic_account:
                        break

            # Group budget CPV lines by their CPV codes from purchase plan lines
            lines_by_cpv = {}

            for cpv_line in filtered_cpv_lines:
                # Find purchase plan lines that use this budget_cpv
                related_plan_lines = purchase_plan_lines.filtered(
                    lambda ppl: ppl.budget_cpv_id.id == cpv_line.budget_cpv_id.id
                )

                for plan_line in related_plan_lines:
                    if plan_line.cpv_id:
                        cpv_key = plan_line.cpv_id.id
                        cpv_name = plan_line.cpv_id.code or plan_line.cpv_id.name

                        if cpv_key not in lines_by_cpv:
                            lines_by_cpv[cpv_key] = {
                                'cpv_name': cpv_name,
                                'cpv_code': plan_line.cpv_id.code,
                                'lines': [],
                                'plan_lines': []
                            }

                        # Add the budget CPV line
                        if cpv_line not in lines_by_cpv[cpv_key]['lines']:
                            lines_by_cpv[cpv_key]['lines'].append(cpv_line)

                        # Add the plan line
                        if plan_line not in lines_by_cpv[cpv_key]['plan_lines']:
                            lines_by_cpv[cpv_key]['plan_lines'].append(plan_line)

            if not lines_by_cpv:
                return {'error': 'No data found to categorize by CPV codes for the selected analytic account'}

            # Prepare chart data
            analytic_account_name = analytic_account.name if analytic_account else f'Account {analytic_account_id}'
            if analytic_account and hasattr(analytic_account, 'code') and analytic_account.code:
                analytic_account_name = f"{analytic_account.code} - {analytic_account_name}"

            chart_data = {
                'pie_chart': {
                    'labels': [],
                    'data': [],
                    'colors': ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6B6B', '#4ECDC4',
                               '#45B7D1', '#96CEB4']
                },
                'bar_chart': {
                    'labels': [],
                    'budget_amounts': [],
                    'used_amounts': [],
                    'remaining_amounts': []
                },
                'summary': {
                    'total_budget': 0,
                    'total_used': 0,
                    'total_remaining': 0,
                    'lines_count': len(filtered_cpv_lines),
                    'cpv_categories': len(lines_by_cpv),
                    'analytic_account_name': analytic_account_name,
                },
                'table_data': []
            }

            # Flag to track if we've set the total_remaining value
            total_remaining_set = False

            # Helper function to get selection field display value
            def get_selection_display(record, field_name):
                if not hasattr(record, field_name):
                    return 'N/A'
                field_value = getattr(record, field_name, False)
                if not field_value:
                    return 'N/A'
                field_obj = record._fields.get(field_name)
                if field_obj and hasattr(field_obj, 'selection'):
                    selection_dict = dict(field_obj.selection)
                    return selection_dict.get(field_value, field_value)
                return field_value

            # Process each CPV category
            for cpv_id, cpv_data in lines_by_cpv.items():
                cpv_name = cpv_data['cpv_name']
                cpv_code = cpv_data['cpv_code']
                lines = cpv_data['lines']
                plan_lines = cpv_data['plan_lines']

                category_budget = 0
                category_used = 0
                category_remaining = 0

                # Calculate totals for this CPV category from budget lines
                for line in lines:
                    budget_amount = line.budget_amount or 0
                    used_amount = line.amount or 0
                    remaining_amount = line.pu_re_am or 0

                    category_budget += budget_amount
                    category_used += used_amount

                    if category_remaining == 0 and remaining_amount > 0:
                        category_remaining = remaining_amount

                    if not total_remaining_set and remaining_amount > 0:
                        chart_data['summary']['total_remaining'] = remaining_amount
                        total_remaining_set = True

                # Add plan line information to table data with new fields
                for line in lines:
                    for plan_line in plan_lines:
                        if line.budget_cpv_id.id == plan_line.budget_cpv_id.id:
                            # Get currency symbol
                            currency_symbol = plan_line.currency_id.symbol if plan_line.currency_id else ''

                            chart_data['table_data'].append({
                                'cpv_name': cpv_name,
                                'plan_name': plan_line.name or f'Plan Line {plan_line.id}',
                                'budget_amount': line.budget_amount or 0,
                                'used_amount': line.amount or 0,
                                'remaining_amount': line.pu_re_am or 0,
                                'budget_line': line.budget_line_id.name if line.budget_line_id else 'N/A',
                                'selected_plan_name': line.selected_plan_name or 'N/A',
                                # New fields from purchase.plan.line
                                'funding_source': get_selection_display(plan_line, 'funding_source'),
                                'purchase_method': plan_line.purchase_method_id.name if plan_line.purchase_method_id else 'N/A',
                                'pricekurant': get_selection_display(plan_line, 'pricekurant'),
                                'variants': ', '.join(plan_line.x_studio_variants.mapped(
                                    'name')) if plan_line.x_studio_variants else 'N/A',
                                'pu_st_am': plan_line.pu_st_am or 0,
                                'pu_ac_am': plan_line.pu_ac_am or 0,
                                'pu_diff': plan_line.pu_diff or 0,
                                'x_studio_reserved': plan_line.x_studio_reserved or 0,
                                'x_studio_remaining_resource': plan_line.x_studio_remaining_resource or 0,
                                'pcon_am': plan_line.pcon_am or 0,
                                'pc_re_am': plan_line.pc_re_am or 0,
                                'paim_am': plan_line.paim_am or 0,
                                'pa_re_am': plan_line.pa_re_am or 0,
                                'currency_symbol': currency_symbol,
                                'budget_lines_allocated': plan_line.budget_lines_allocated or 0,
                                'remaining_to_allocate': plan_line.remaining_to_allocate or 0,
                            })

                # Add category to charts
                chart_data['pie_chart']['labels'].append(f'{cpv_name} ({len(lines)} lines)')
                chart_data['pie_chart']['data'].append(category_budget)

                bar_label = cpv_name[:20] + '...' if len(cpv_name) > 20 else cpv_name
                chart_data['bar_chart']['labels'].append(bar_label)
                chart_data['bar_chart']['budget_amounts'].append(category_budget)
                chart_data['bar_chart']['used_amounts'].append(category_used)
                chart_data['bar_chart']['remaining_amounts'].append(category_remaining)

                chart_data['summary']['total_budget'] += category_budget
                chart_data['summary']['total_used'] += category_used

            return chart_data

        except Exception as e:
            return {'error': str(e)}