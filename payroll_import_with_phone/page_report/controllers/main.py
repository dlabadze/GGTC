# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
from collections import defaultdict


class AccountingDashboardController(http.Controller):

    @http.route('/accounting/dashboard', type='http', auth='user', website=True)
    def accounting_dashboard(self, date_from=None, date_to=None, month_from=None, month_to=None, **kwargs):
        """Main dashboard page based on Excel schema"""
        dashboard_data = self._get_dashboard_data(date_from, date_to, month_from, month_to)

        return request.render('page_report.accounting_dashboard_template', {
            'dashboard_data': dashboard_data,
            'user_name': request.env.user.name,
            'company': request.env.user.company_id.name,
        })

    @http.route('/accounting/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self, date_from=None, date_to=None, month_from=None, month_to=None, **kwargs):
        """API endpoint for dashboard data"""
        try:
            dashboard_data = self._get_dashboard_data(date_from, date_to, month_from, month_to)
            return {
                'success': True,
                'data': dashboard_data,
                'timestamp': str(datetime.now())
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _get_dashboard_data(self, date_from=None, date_to=None, month_from=None, month_to=None):
        """Get accounting dashboard data from account.move and account.move.line"""

        # Set default dates (current year)
        if not date_from:
            date_from = datetime.now().replace(month=1, day=1).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')

        # Set default months (current year, but only current month if no filter)
        if not month_from or not month_to:
            current_date = datetime.now()
            month_from = f"{current_date.year}-{current_date.month:02d}"  # Current month only
            month_to = f"{current_date.year}-{current_date.month:02d}"  # Current month only

        # Get customer invoices (account.move)
        invoice_domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]

        invoices = request.env['account.move'].search(invoice_domain)

        # Get invoice lines (account.move.line)
        invoice_lines = request.env['account.move.line'].search([
            ('move_id', 'in', invoices.ids),
            ('product_id', '!=', False),
            ('display_type', 'in', [False, 'product']),  # Only product lines
        ])

        # Calculate dashboard metrics
        dashboard_data = {
            'summary': self._calculate_summary(invoices, invoice_lines),
            'top_products': self._get_top_products(invoice_lines),
            'top_customers': self._get_top_customers(invoices),
            'top_categories': self._get_top_categories(invoice_lines),
            'monthly_data': self._get_monthly_data(invoices, invoice_lines, month_from, month_to),
            'date_from': date_from,
            'date_to': date_to,
            'month_from': month_from,
            'month_to': month_to,
        }

        return dashboard_data

    def _calculate_summary(self, invoices, invoice_lines):
        """Calculate summary metrics"""
        total_revenue_with_tax = sum(invoices.mapped('amount_total'))
        total_revenue_without_tax = sum(invoices.mapped('amount_untaxed'))
        total_quantity = sum(invoice_lines.mapped('quantity'))

        # Find top product, customer, category
        top_product = self._get_top_products(invoice_lines, limit=1)
        top_customer = self._get_top_customers(invoices, limit=1)
        top_category = self._get_top_categories(invoice_lines, limit=1)

        return {
            'total_revenue_with_tax': total_revenue_with_tax,
            'total_revenue_without_tax': total_revenue_without_tax,
            'total_quantity': total_quantity,
            'total_invoices': len(invoices),
            'top_product': top_product[0] if top_product else None,
            'top_customer': top_customer[0] if top_customer else None,
            'top_category': top_category[0] if top_category else None,
        }

    def _get_top_products(self, invoice_lines, limit=10):
        """Get top products by revenue (matching Excel structure)"""
        product_data = defaultdict(lambda: {
            'revenue_with_tax': 0,
            'revenue_without_tax': 0,
            'quantity': 0,
            'name': '',
            'product_id': 0
        })

        for line in invoice_lines:
            if line.product_id:
                key = line.product_id.id
                product_data[key]['name'] = line.product_id.name or line.name
                product_data[key]['product_id'] = line.product_id.id
                product_data[key]['revenue_with_tax'] += line.price_total
                product_data[key]['revenue_without_tax'] += line.price_subtotal
                product_data[key]['quantity'] += line.quantity

        # Sort by revenue and calculate percentages
        total_revenue = sum(p['revenue_with_tax'] for p in product_data.values())
        products = list(product_data.values())
        products.sort(key=lambda x: x['revenue_with_tax'], reverse=True)

        # Add percentage and ranking
        for i, product in enumerate(products[:limit]):
            product['rank'] = i + 1
            product['percentage'] = (product['revenue_with_tax'] / total_revenue * 100) if total_revenue > 0 else 0

        return products[:limit]

    def _get_top_customers(self, invoices, limit=10):
        """Get top customers by revenue"""
        customer_data = defaultdict(lambda: {
            'revenue_with_tax': 0,
            'revenue_without_tax': 0,
            'invoice_count': 0,
            'name': '',
            'partner_id': 0
        })

        for invoice in invoices:
            if invoice.partner_id:
                key = invoice.partner_id.id
                customer_data[key]['name'] = invoice.partner_id.name
                customer_data[key]['partner_id'] = invoice.partner_id.id
                customer_data[key]['revenue_with_tax'] += invoice.amount_total
                customer_data[key]['revenue_without_tax'] += invoice.amount_untaxed
                customer_data[key]['invoice_count'] += 1

        # Sort by revenue and calculate percentages
        total_revenue = sum(c['revenue_with_tax'] for c in customer_data.values())
        customers = list(customer_data.values())
        customers.sort(key=lambda x: x['revenue_with_tax'], reverse=True)

        # Add percentage and ranking
        for i, customer in enumerate(customers[:limit]):
            customer['rank'] = i + 1
            customer['percentage'] = (customer['revenue_with_tax'] / total_revenue * 100) if total_revenue > 0 else 0

        return customers[:limit]

    def _get_top_categories(self, invoice_lines, limit=10):
        """Get top product categories by revenue"""
        category_data = defaultdict(lambda: {
            'revenue_with_tax': 0,
            'revenue_without_tax': 0,
            'quantity': 0,
            'name': '',
            'category_id': 0
        })

        for line in invoice_lines:
            if line.product_id and line.product_id.categ_id:
                key = line.product_id.categ_id.id
                category_data[key]['name'] = line.product_id.categ_id.name
                category_data[key]['category_id'] = line.product_id.categ_id.id
                category_data[key]['revenue_with_tax'] += line.price_total
                category_data[key]['revenue_without_tax'] += line.price_subtotal
                category_data[key]['quantity'] += line.quantity

        # Sort by revenue and calculate percentages
        total_revenue = sum(c['revenue_with_tax'] for c in category_data.values())
        categories = list(category_data.values())
        categories.sort(key=lambda x: x['revenue_with_tax'], reverse=True)

        # Add percentage and ranking
        for i, category in enumerate(categories[:limit]):
            category['rank'] = i + 1
            category['percentage'] = (category['revenue_with_tax'] / total_revenue * 100) if total_revenue > 0 else 0

        return categories[:limit]

    def _get_monthly_data(self, invoices, invoice_lines, month_from=None, month_to=None):
        """Get monthly revenue and quantity data with dynamic columns"""
        from datetime import datetime
        from calendar import month_name

        # Set default months if not provided
        current_year = datetime.now().year
        if not month_from:
            month_from = f"{current_year}-01"  # January of current year
        if not month_to:
            month_to = f"{current_year}-12"  # December of current year

        # Parse month range
        try:
            start_year, start_month = map(int, month_from.split('-'))
            end_year, end_month = map(int, month_to.split('-'))
        except:
            # Fallback to current year
            start_year, start_month = current_year, 1
            end_year, end_month = current_year, 12

        # Generate list of months in the range
        months_list = []
        year, month = start_year, start_month

        while (year < end_year) or (year == end_year and month <= end_month):
            month_key = f"{year}-{month:02d}"
            month_display = f"{month_name[month]} {year}"
            months_list.append({
                'key': month_key,
                'display': month_display,
                'short': month_name[month][:3]
            })

            month += 1
            if month > 12:
                month = 1
                year += 1

        # Initialize data structures
        revenue_by_category = defaultdict(lambda: {month['key']: 0 for month in months_list})
        quantity_by_category = defaultdict(lambda: {month['key']: 0 for month in months_list})

        # Process invoices for revenue
        for invoice in invoices:
            if invoice.invoice_date:
                invoice_month = invoice.invoice_date.strftime('%Y-%m')
                if any(month['key'] == invoice_month for month in months_list):
                    # Group by customer or category - you can change this logic
                    category = 'Total Revenue'
                    revenue_by_category[category][invoice_month] += invoice.amount_total

        # Process invoice lines for quantity by product category
        for line in invoice_lines:
            if line.move_id.invoice_date:
                line_month = line.move_id.invoice_date.strftime('%Y-%m')
                if any(month['key'] == line_month for month in months_list):
                    category = line.product_id.categ_id.name if line.product_id and line.product_id.categ_id else 'Other'
                    quantity_by_category[category][line_month] += line.quantity

        return {
            'months': months_list,
            'revenue_by_category': dict(revenue_by_category),
            'quantity_by_category': dict(quantity_by_category),
            'month_from': month_from,
            'month_to': month_to
        }

    @http.route('/accounting/dashboard/months', type='json', auth='user')
    def get_monthly_data(self, month_from=None, month_to=None, **kwargs):
        """API endpoint specifically for monthly data"""
        try:
            # Get invoices for the full year to ensure we have data
            current_year = datetime.now().year
            year_start = f"{current_year}-01-01"
            year_end = f"{current_year}-12-31"

            invoice_domain = [
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', year_start),
                ('invoice_date', '<=', year_end),
            ]

            invoices = request.env['account.move'].search(invoice_domain)
            invoice_lines = request.env['account.move.line'].search([
                ('move_id', 'in', invoices.ids),
                ('product_id', '!=', False),
                ('display_type', 'in', [False, 'product']),
            ])

            monthly_data = self._get_monthly_data(invoices, invoice_lines, month_from, month_to)

            return {
                'success': True,
                'data': monthly_data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }