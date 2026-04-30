from odoo import http
from odoo.http import request


class PurchasePlanReportController(http.Controller):

    @http.route('/purchase_plan_report', type='http', auth='user', website=True)
    def purchase_plan_report(self, **kwargs):
        """Main visual report page — lists all purchase plans for selection."""
        purchase_plans = request.env['purchase.plan'].search([], order='name asc')
        return request.render(
            'purchase_plan_budget_report.purchase_plan_report_template',
            {'purchase_plans': purchase_plans},
        )

    @http.route('/purchase_plan_report/get_data', type='json', auth='user')
    def get_report_data(self, plan_id):
        """Return all purchase.plan.lines whose budget.cpv.lines contain
        at least one line with pu_re_am < 0, together with those negative lines."""
        try:
            if not plan_id:
                return {'error': 'Plan ID is required'}

            plan = request.env['purchase.plan'].browse(int(plan_id))
            if not plan.exists():
                return {'error': 'Purchase plan not found'}

            funding_source_labels = {
                '1': 'სახელმწიფო ბიუჯეტი',
                '2': 'ავტ. რეს. ბიუჯეტი',
                '3': 'ადგილობრივი ბიუჯეტი',
                '4': 'საკუთარი სახსრები',
                '5': 'გრანტი/კრედიტი',
            }

            result_lines = []
            for plan_line in plan.line_ids:
                if not plan_line.budget_cpv_id:
                    continue

                negative_cpv_lines = plan_line.budget_cpv_id.line_ids.filtered(
                    lambda cl: cl.pu_re_am < 0
                )
                if not negative_cpv_lines:
                    continue

                cpv_line_data = []
                for cl in negative_cpv_lines:
                    cpv_line_data.append({
                        'budget_line_name': cl.plan2_display or (
                            cl.budget_line_id.display_name if cl.budget_line_id else '-'
                        ),
                        'selected_plan_name': cl.selected_plan_name or '-',
                        'budget_amount': cl.budget_amount or 0,
                        'amount': cl.amount or 0,
                        'pu_re_am': cl.pu_re_am or 0,
                        'currency_symbol': (
                            cl.currency_id.symbol if cl.currency_id else ''
                        ),
                    })

                result_lines.append({
                    'id': plan_line.id,
                    'cpv_code': plan_line.cpv_id.code if plan_line.cpv_id else '-',
                    'cpv_name': plan_line.cpv_name or '-',
                    'funding_source': funding_source_labels.get(
                        plan_line.funding_source, '-'
                    ) if plan_line.funding_source else '-',
                    'purchase_method': (
                        plan_line.purchase_method_id.name
                        if plan_line.purchase_method_id else '-'
                    ),
                    'pu_st_am': plan_line.pu_st_am or 0,
                    'pu_ac_am': plan_line.pu_ac_am or 0,
                    'pcon_am': plan_line.pcon_am or 0,
                    'paim_am': plan_line.paim_am or 0,
                    'currency_symbol': (
                        plan_line.currency_id.symbol if plan_line.currency_id else ''
                    ),
                    'negative_cpv_lines': cpv_line_data,
                })

            return {
                'plan_name': plan.name,
                'start_date': plan.start_date.strftime('%d.%m.%Y') if plan.start_date else '',
                'end_date': plan.end_date.strftime('%d.%m.%Y') if plan.end_date else '',
                'lines': result_lines,
                'total_lines': len(result_lines),
            }

        except Exception as e:
            return {'error': str(e)}
