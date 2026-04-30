from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class PartnerCurrencyMovementReportWizard(models.TransientModel):
    _name = 'partner.currency.movement.report.wizard'
    _description = 'Partner Currency Movement Report Wizard'

    # Date range fields
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=lambda self: date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=lambda self: date.today()
    )
    
    # Filter fields
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners',
        domain=[('is_company', '=', True)]
    )
    
    partner_category_filter = fields.Selection([
        ('all', 'All Partners'),
        ('customer', 'Customers Only'),
        ('vendor', 'Vendors Only'),
        ('employee', 'Employees Only'),
        ('customer_vendor', 'Customers & Vendors'),
    ], string='Partner Type Filter', default='all', required=True)
    
    account_ids = fields.Many2many(
        'account.account',
        string='Accounts',
        domain=[('deprecated', '=', False), ('account_type', 'in', ['asset_receivable', 'liability_payable'])]
    )
    
    currency_ids = fields.Many2many(
        'res.currency',
        string='Currencies'
    )
    
    # Display options
    show_zero_balance = fields.Boolean(
        string='Show Zero Balances',
        default=False,
        help="Include lines with zero opening balance, closing balance, and no movements"
    )
    
    group_by_partner = fields.Boolean(
        string='Group by Partner',
        default=True,
        help="Group results by partner first"
    )
    
    group_by_currency = fields.Boolean(
        string='Group by Currency',
        default=True,
        help="Group results by currency within partner groups"
    )
    
    # Report format options
    report_format = fields.Selection([
        ('list', 'List View'),
        ('pivot', 'Pivot Table'),
        ('graph', 'Graph View'),
        ('pdf', 'PDF Report'),
    ], string='Report Format', default='list', required=True)

    @api.onchange('partner_category_filter')
    def _onchange_partner_category_filter(self):
        """Update partner domain based on category filter"""
        if self.partner_category_filter == 'customer':
            domain = [('customer_rank', '>', 0)]
        elif self.partner_category_filter == 'vendor':
            domain = [('supplier_rank', '>', 0)]
        elif self.partner_category_filter == 'employee':
            domain = [('employee_ids', '!=', False)]
        elif self.partner_category_filter == 'customer_vendor':
            domain = ['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)]
        else:
            domain = []
        
        return {'domain': {'partner_ids': domain}}

    @api.onchange('date_from', 'date_to')
    def _onchange_dates(self):
        """Validate date range"""
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError(_('The start date cannot be later than the end date.'))

    def _prepare_report_options(self):
        """Prepare options for report generation"""
        options = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'show_zero_balance': self.show_zero_balance,
            'group_by_partner': self.group_by_partner,
            'group_by_currency': self.group_by_currency,
        }
        
        # Add filters if specified
        if self.partner_ids:
            options['partner_ids'] = self.partner_ids.ids
        elif self.partner_category_filter != 'all':
            # Apply category filter
            if self.partner_category_filter == 'customer':
                partners = self.env['res.partner'].search([('customer_rank', '>', 0)])
            elif self.partner_category_filter == 'vendor':
                partners = self.env['res.partner'].search([('supplier_rank', '>', 0)])
            elif self.partner_category_filter == 'employee':
                partners = self.env['res.partner'].search([('employee_ids', '!=', False)])
            elif self.partner_category_filter == 'customer_vendor':
                partners = self.env['res.partner'].search(['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)])
            else:
                partners = self.env['res.partner']
            
            if partners:
                options['partner_ids'] = partners.ids
        
        if self.account_ids:
            options['account_ids'] = self.account_ids.ids
        
        if self.currency_ids:
            options['currency_ids'] = self.currency_ids.ids
        
        return options

    def action_generate_report(self):
        """Generate and display the report"""
        self.ensure_one()
        
        # Prepare options
        options = self._prepare_report_options()
        
        # Generate report data
        report = self.env['partner.currency.movement.report'].generate_report_data(options)
        
        # Determine the view to show based on format
        if self.report_format == 'pdf':
            return self._generate_pdf_report(report)
        elif self.report_format == 'pivot':
            return self._open_pivot_view(report)
        elif self.report_format == 'graph':
            return self._open_graph_view(report)
        else:
            return self._open_list_view(report)

    def _open_list_view(self, report):
        """Open the list view of the report"""
        return {
            'name': _('Partner Currency Movement Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.currency.movement.report.line',
            'view_mode': 'list,form',
            'domain': [('report_id', '=', report.id)],
            'context': {
                'search_default_group_by_partner': self.group_by_partner,
                'search_default_group_by_currency': self.group_by_currency,
                'default_report_id': report.id,
            },
            'target': 'current',
        }

    def _open_pivot_view(self, report):
        """Open the pivot view of the report"""
        return {
            'name': _('Partner Currency Movement Report - Pivot'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.currency.movement.report.line',
            'view_mode': 'pivot,list,form',
            'domain': [('report_id', '=', report.id)],
            'context': {
                'default_report_id': report.id,
            },
            'target': 'current',
        }

    def _open_graph_view(self, report):
        """Open the graph view of the report"""
        return {
            'name': _('Partner Currency Movement Report - Graph'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.currency.movement.report.line',
            'view_mode': 'graph,list,form',
            'domain': [('report_id', '=', report.id)],
            'context': {
                'default_report_id': report.id,
            },
            'target': 'current',
        }

    def _generate_pdf_report(self, report):
        """Generate PDF report"""
        return self.env.ref('account_partner_currency_movement_report.action_partner_currency_report_pdf').report_action(report)

    def action_preview_report(self):
        """Preview the report without generating it"""
        options = self._prepare_report_options()
        
        # Count potential lines
        move_lines = self.env['account.move.line'].search([
            ('date', '<=', options['date_to']),
            ('company_id', '=', options['company_id']),
            ('parent_state', '=', 'posted'),
            ('partner_id', '!=', False),
            ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),
        ])
        
        partners_count = len(move_lines.mapped('partner_id'))
        currencies_count = len(move_lines.mapped('currency_id'))
        accounts_count = len(move_lines.mapped('account_id'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Report Preview'),
                'message': _(
                    'Report will include approximately:\n'
                    '• %s partners\n'
                    '• %s currencies\n'
                    '• %s accounts\n'
                    '• Period: %s to %s'
                ) % (partners_count, currencies_count, accounts_count, self.date_from, self.date_to),
                'type': 'info',
                'sticky': False,
            }
        } 