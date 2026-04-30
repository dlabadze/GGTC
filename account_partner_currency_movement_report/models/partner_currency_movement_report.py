from odoo import api, fields, models, _
from odoo.tools import float_round
from collections import defaultdict
from datetime import datetime


class PartnerCurrencyMovementReport(models.TransientModel):
    _name = 'partner.currency.movement.report'
    _description = 'Partner Currency Movement Report'

    name = fields.Char(string='Report Name', default='Partner Currency Movement Report')
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True)
    line_ids = fields.One2many('partner.currency.movement.report.line', 'report_id', string='Report Lines')

    @api.model
    def generate_report_data(self, options):
        """Generate the report data based on the provided options"""
        
        # Create report record
        report = self.create({
            'name': f"Partner Currency Movement Report - {options['date_from']} to {options['date_to']}",
            'date_from': options['date_from'],
            'date_to': options['date_to'],
            'company_id': options['company_id'],
        })
        
        # Get report lines
        lines_data = self._get_report_lines(options)
        
        # Create report lines
        report_lines = []
        for line_data in lines_data:
            line_data['report_id'] = report.id
            report_lines.append(line_data)
        
        if report_lines:
            self.env['partner.currency.movement.report.line'].create(report_lines)
        
        return report

    def _get_report_lines(self, options):
        """Get the detailed report lines with partner currency movements"""
        
        # Build domain for account move lines
        domain = self._build_domain(options)
        
        # Get account move lines with partners
        move_lines = self.env['account.move.line'].search(domain)
        
        # Group by partner, currency and account
        grouped_data = self._group_move_lines(move_lines, options)
        
        # Calculate balances and movements
        report_lines = self._calculate_movements(grouped_data, options)
        
        return report_lines

    def _build_domain(self, options):
        """Build the domain for filtering account move lines"""
        domain = [
            ('date', '<=', options['date_to']),
            ('company_id', '=', options['company_id']),
            ('parent_state', '=', 'posted'),  # Only posted entries
            ('partner_id', '!=', False),  # Only entries with partners
            ('account_id.account_type', 'in', ['asset_receivable', 'liability_payable']),  # Only receivable/payable accounts
        ]
        
        # Partner filter
        if options.get('partner_ids'):
            domain.append(('partner_id', 'in', options['partner_ids']))
        
        # Account filter
        if options.get('account_ids'):
            domain.append(('account_id', 'in', options['account_ids']))
        
        # Currency filter - disabled for now, show all currencies
        # if options.get('currency_ids'):
        #     domain.append(('currency_id', 'in', options['currency_ids']))
        
        return domain

    def _group_move_lines(self, move_lines, options):
        """Group move lines by partner, currency and account"""
        grouped = defaultdict(lambda: {
            'partner': None,
            'account': None,
            'currency': None,
            'opening_balance': 0.0,
            'closing_balance': 0.0,
            'total_debit': 0.0,
            'total_credit': 0.0,
            'move_lines': []
        })
        
        for line in move_lines:
            # Group by partner, account and the actual transaction currency
            # We already filtered by account currency in the domain
            key = (line.partner_id.id, line.account_id.id, line.currency_id.id)
            group = grouped[key]
            
            if not group['partner']:
                group['partner'] = line.partner_id
                group['account'] = line.account_id
                group['currency'] = line.currency_id
            
            group['move_lines'].append(line)
            
            # Determine if this is in the period or before
            if line.date < options['date_from']:
                # Opening balance calculation
                if line.currency_id == line.company_currency_id:
                    group['opening_balance'] += line.balance
                else:
                    group['opening_balance'] += line.amount_currency
            else:
                # Period movements
                if line.currency_id == line.company_currency_id:
                    group['total_debit'] += line.debit
                    group['total_credit'] += line.credit
                else:
                    # For foreign currency, use amount_currency
                    if line.amount_currency > 0:
                        group['total_debit'] += line.amount_currency
                    else:
                        group['total_credit'] += abs(line.amount_currency)
        
        # Calculate closing balances
        for group in grouped.values():
            group['closing_balance'] = group['opening_balance'] + group['total_debit'] - group['total_credit']
        
        return grouped

    def _calculate_movements(self, grouped_data, options):
        """Calculate final movements and prepare report lines"""
        report_lines = []
        
        for (partner_id, account_id, currency_id), data in grouped_data.items():
            
            # Skip zero balances if not requested
            if not options.get('show_zero_balance', False):
                if (data['opening_balance'] == 0 and 
                    data['closing_balance'] == 0 and 
                    data['total_debit'] == 0 and 
                    data['total_credit'] == 0):
                    continue
            
            # Create report line
            line_data = {
                'partner_id': partner_id,
                'account_id': account_id,
                'currency_id': currency_id,
                'opening_balance': float_round(data['opening_balance'], precision_digits=2),
                'closing_balance': float_round(data['closing_balance'], precision_digits=2),
                'total_debit': float_round(data['total_debit'], precision_digits=2),
                'total_credit': float_round(data['total_credit'], precision_digits=2),
                'net_movement': float_round(data['total_debit'] - data['total_credit'], precision_digits=2),
                'move_line_count': len(data['move_lines']),
            }
            
            report_lines.append(line_data)
        
        # Sort by partner name, then currency, then account code
        report_lines.sort(key=lambda x: (
            self.env['res.partner'].browse(x['partner_id']).name,
            self.env['res.currency'].browse(x['currency_id']).name,
            self.env['account.account'].browse(x['account_id']).code
        ))
        
        return report_lines


class PartnerCurrencyMovementReportLine(models.TransientModel):
    _name = 'partner.currency.movement.report.line'
    _description = 'Partner Currency Movement Report Line'
    _order = 'partner_name, currency_name, account_code'

    report_id = fields.Many2one('partner.currency.movement.report', string='Report', ondelete='cascade')
    
    # Partner information
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    partner_name = fields.Char(related='partner_id.name', string='Partner Name')
    partner_category = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('employee', 'Employee'),
        ('other', 'Other')
    ], string='Partner Type', compute='_compute_partner_category', store=False)
    
    # Account information
    account_id = fields.Many2one('account.account', string='Account', required=True)
    account_code = fields.Char(related='account_id.code', string='Account Code')
    account_name = fields.Char(related='account_id.name', string='Account Name')
    
    # Currency information
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    currency_name = fields.Char(related='currency_id.name', string='Currency')
    currency_symbol = fields.Char(related='currency_id.symbol', string='Symbol')
    
    # Balance and movement fields
    opening_balance = fields.Monetary(
        string='Opening Balance',
        currency_field='currency_id',
        help="Balance at the beginning of the period"
    )
    closing_balance = fields.Monetary(
        string='Closing Balance',
        currency_field='currency_id',
        help="Balance at the end of the period"
    )
    total_debit = fields.Monetary(
        string='Total Debit',
        currency_field='currency_id',
        help="Total debit movements in the period"
    )
    total_credit = fields.Monetary(
        string='Total Credit',
        currency_field='currency_id',
        help="Total credit movements in the period"
    )
    net_movement = fields.Monetary(
        string='Net Movement',
        currency_field='currency_id',
        help="Net movement in the period (Debit - Credit)"
    )
    
    # Additional information
    move_line_count = fields.Integer(
        string='Number of Moves',
        help="Number of journal entries for this partner, currency and account"
    )
    
    # Computed display name
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name'
    )

    @api.depends('partner_id')
    def _compute_partner_category(self):
        for record in self:
            if record.partner_id:
                if record.partner_id.is_company and record.partner_id.supplier_rank > 0:
                    record.partner_category = 'vendor'
                elif record.partner_id.customer_rank > 0:
                    record.partner_category = 'customer'
                elif hasattr(record.partner_id, 'employee_ids') and record.partner_id.employee_ids:
                    record.partner_category = 'employee'
                else:
                    record.partner_category = 'other'
            else:
                record.partner_category = 'other'

    @api.depends('partner_id', 'currency_id', 'account_id')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id and record.currency_id and record.account_id:
                record.display_name = f"{record.partner_id.name} - {record.currency_id.name} - {record.account_id.code}"
            else:
                record.display_name = "Partner Currency Movement Line"

    def action_view_move_lines(self):
        """Open the related journal items"""
        self.ensure_one()
        
        # Build domain for related move lines
        domain = [
            ('partner_id', '=', self.partner_id.id),
            ('account_id', '=', self.account_id.id),
            ('currency_id', '=', self.currency_id.id),
            ('date', '>=', self.report_id.date_from),
            ('date', '<=', self.report_id.date_to),
            ('company_id', '=', self.report_id.company_id.id),
            ('parent_state', '=', 'posted'),
        ]
        
        return {
            'name': _('Journal Items - %s (%s - %s)') % (self.partner_id.name, self.currency_id.name, self.account_id.code),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {
                'search_default_group_by_partner': 1,
                'search_default_group_by_date': 1,
            },
            'target': 'current',
        } 