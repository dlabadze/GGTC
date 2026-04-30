from odoo import api, models


class PartnerCurrencyMovementReportTemplate(models.AbstractModel):
    _name = 'report.partner_currency_movement_report.partner_currency_pdf'
    _description = 'Partner Currency Movement Report Template'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Prepare data for the PDF report template"""
        
        # Get report records
        reports = self.env['partner.currency.movement.report'].browse(docids)
        
        if not reports:
            return {}
        
        report = reports[0]  # Single report for now
        
        # Get report lines grouped by partner and currency
        grouped_lines = self._group_lines_for_pdf(report.line_ids)
        
        # Calculate totals
        totals = self._calculate_totals(report.line_ids)
        
        return {
            'doc_ids': docids,
            'doc_model': 'partner.currency.movement.report',
            'docs': reports,
            'report': report,
            'grouped_lines': grouped_lines,
            'totals': totals,
            'company': report.company_id,
        }

    def _group_lines_for_pdf(self, lines):
        """Group lines by partner and currency for better PDF layout"""
        grouped = {}
        
        for line in lines:
            partner_key = line.partner_id.id
            if partner_key not in grouped:
                grouped[partner_key] = {
                    'partner': line.partner_id,
                    'currencies': {}
                }
            
            currency_key = line.currency_id.id
            if currency_key not in grouped[partner_key]['currencies']:
                grouped[partner_key]['currencies'][currency_key] = {
                    'currency': line.currency_id,
                    'accounts': []
                }
            
            grouped[partner_key]['currencies'][currency_key]['accounts'].append(line)
        
        # Sort partners by name
        sorted_partners = sorted(grouped.items(), key=lambda x: x[1]['partner'].name)
        
        # Sort currencies and accounts within each partner
        for partner_id, partner_data in sorted_partners:
            sorted_currencies = sorted(
                partner_data['currencies'].items(),
                key=lambda x: x[1]['currency'].name
            )
            partner_data['currencies'] = dict(sorted_currencies)
            
            # Sort accounts within each currency
            for currency_id, currency_data in partner_data['currencies'].items():
                currency_data['accounts'].sort(key=lambda x: x.account_code)
        
        return dict(sorted_partners)

    def _calculate_totals(self, lines):
        """Calculate total amounts for the report"""
        totals = {
            'opening_balance': 0.0,
            'total_debit': 0.0,
            'total_credit': 0.0,
            'net_movement': 0.0,
            'closing_balance': 0.0,
            'move_count': 0,
        }
        
        for line in lines:
            # Convert to company currency for totals
            # For simplicity, we'll sum the amounts as-is
            # In a real implementation, you might want to convert to company currency
            totals['opening_balance'] += line.opening_balance
            totals['total_debit'] += line.total_debit
            totals['total_credit'] += line.total_credit
            totals['net_movement'] += line.net_movement
            totals['closing_balance'] += line.closing_balance
            totals['move_count'] += line.move_line_count
        
        return totals 