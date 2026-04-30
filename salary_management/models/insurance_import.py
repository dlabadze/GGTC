from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import pandas as pd
import io
import logging

_logger = logging.getLogger(__name__)

class InsuranceImport(models.Model):
    _name = 'insurance.import'
    _description = 'Insurance Import'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    excel_file = fields.Binary(string='Excel File', required=True)
    excel_filename = fields.Char(string='File Name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('imported', 'Imported'),
        ('posted', 'Posted')
    ], string='Status', default='draft', copy=False)
    line_ids = fields.One2many('insurance.import.line', 'import_id', string='Insurance Lines')
    journal_entry_count = fields.Integer(compute='_compute_journal_entry_count')
    journal_entry_ids = fields.Many2many('account.move', string='Journal Entries', copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('insurance.import') or _('New')
        return super(InsuranceImport, self).create(vals)
    
    def _compute_journal_entry_count(self):
        for record in self:
            record.journal_entry_count = len(record.journal_entry_ids)
    
    def action_import_excel(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))
        
        try:
            excel_data = base64.b64decode(self.excel_file)
            df = pd.read_excel(io.BytesIO(excel_data), engine='xlrd', skiprows=2)  # Skip first 2 rows
            _logger.info(f'DataFrame loaded with columns: {df.columns.tolist()}')
            
            # Mapping of columns based on the Excel structure
            columns_map = {
                'partner_id': df.columns[1],      # პირადი ნომერი
                'full_name': df.columns[2],        # სახელი, გვარი
                'base_salary': df.columns[3],      # ძირითადი ხელფასი
                'total_salary': df.columns[6],     # დარიცხული ხელფასი
                'pension': df.columns[7],          # საპენსიო 2%
                'company_tax': df.columns[8],      # კომპანიის გადასახადი
                'income_tax': df.columns[10],      # საშემოსავლო
                'net_amount': df.columns[11]       # ხელზე ასაღები
            }
            
            # Clear existing lines
            self.line_ids.unlink()
            
            # Safe float conversion - returns 0 if empty or invalid
            def safe_float(value):
                try:
                    if pd.isna(value):
                        return 0.0
                    val = float(value or 0)
                    return val if val > 0 else 0.0
                except:
                    return 0.0
            
            for record in df.to_dict('records'):
                # Skip rows with NaN or empty values
                if pd.isna(record.get(columns_map['partner_id'], None)):
                    continue
                
                # Clean the identification number (remove .0 if present, preserve leading zeros)
                vat = str(record[columns_map['partner_id']]).split('.')[0].zfill(11)
                partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)
                
                # Create insurance line
                line_vals = {
                    'import_id': self.id,
                    'partner_id': partner.id if partner else False,
                    'partner_vat': vat,
                    'full_name': record[columns_map['full_name']],
                    'base_salary': safe_float(record[columns_map['base_salary']]),
                    'total_salary': safe_float(record[columns_map['total_salary']]),
                    'pension': safe_float(record[columns_map['pension']]),
                    'company_tax': safe_float(record[columns_map['company_tax']]),
                    'income_tax': safe_float(record[columns_map['income_tax']]),
                    'net_amount': safe_float(record[columns_map['net_amount']])
                }
                
                # Create the line only if partner is found
                if partner:
                    self.env['insurance.import.line'].create(line_vals)
            
            # Update state to imported
            self.state = 'imported'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Insurance data has been imported successfully.'),
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error('Error processing Excel file: %s', str(e))
            raise UserError(str(e))

    def search_pension_lines(self, min_value=0):
        """Search for insurance import lines with pension contributions above specified threshold"""
        return self.line_ids.search_pension_records(min_value)
    
    def action_view_journal_entries(self):
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.journal_entry_ids.ids)],
        }
    
    def action_generate_journal_entries(self):
        self.ensure_one()
        if self.state == 'posted':
            raise UserError(_("Journal entries have already been generated."))
        
        if not self.line_ids:
            raise UserError(_("No insurance lines to process."))
        
        journal_entries = self.env['account.move']
        
        # Get general journal
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if not journal:
            raise UserError(_("No general journal found."))
        
        # Get required accounts - Note changed 7410 to 7440
        account_7440 = self.env['account.account'].search([('code', '=', '7440')], limit=1)
        account_3130 = self.env['account.account'].search([('code', '=', '3130')], limit=1)
        account_3370 = self.env['account.account'].search([('code', '=', '3370')], limit=1)
        account_7415 = self.env['account.account'].search([('code', '=', '7415')], limit=1)
        account_3320 = self.env['account.account'].search([('code', '=', '3320')], limit=1)
        
        if not all([account_7440, account_3130, account_3370, account_7415, account_3320]):
            missing = []
            if not account_7440: missing.append('7440')
            if not account_3130: missing.append('3130')
            if not account_3370: missing.append('3370')
            if not account_7415: missing.append('7415')
            if not account_3320: missing.append('3320')
            raise UserError(_("Required accounts not found: %s") % ', '.join(missing))
        
        for line in self.line_ids:
            if not line.partner_id:
                continue
            
            try:
                # Create a single journal entry with all line items
                move_lines = []
                
                # 1. Main insurance entry
                move_lines.extend([
                    # Insurance expense debit (7440)
                    (0, 0, {
                        'account_id': account_7440.id,
                        'partner_id': line.partner_id.id,
                        'debit': line.total_salary,
                        'credit': 0,
                        'name': f"{line.partner_id.name} - Insurance Expense"
                    }),
                    # Insurance credit (3130)
                    (0, 0, {
                        'account_id': account_3130.id,
                        'partner_id': line.partner_id.id,
                        'debit': 0,
                        'credit': line.total_salary,
                        'name': f"{line.partner_id.name} - Insurance Payable"
                    })
                ])
                
                # 2. Pension entries if applicable
                if line.pension > 0:
                    move_lines.extend([
                        # Pension debit (3130)
                        (0, 0, {
                            'account_id': account_3130.id,
                            'partner_id': line.partner_id.id,
                            'debit': line.pension,
                            'credit': 0,
                            'name': f"{line.partner_id.name} - Pension"
                        }),
                        # Pension credit (3370)
                        (0, 0, {
                            'account_id': account_3370.id,
                            'partner_id': line.partner_id.id,
                            'debit': 0,
                            'credit': line.pension,
                            'name': f"{line.partner_id.name} - Pension Liability"
                        })
                    ])
                
                # 3. Company tax entries if applicable
                if line.company_tax > 0:
                    move_lines.extend([
                        # Company tax debit (7415)
                        (0, 0, {
                            'account_id': account_7415.id,
                            'partner_id': line.partner_id.id,
                            'debit': line.company_tax,
                            'credit': 0,
                            'name': f"{line.partner_id.name} - Company Tax"
                        }),
                        # Company tax credit (3370)
                        (0, 0, {
                            'account_id': account_3370.id,
                            'partner_id': line.partner_id.id,
                            'debit': 0,
                            'credit': line.company_tax,
                            'name': f"{line.partner_id.name} - Company Tax Liability"
                        })
                    ])
                
                # 4. Income tax entries if applicable
                if line.income_tax > 0:
                    move_lines.extend([
                        # Income tax debit (3130)
                        (0, 0, {
                            'account_id': account_3130.id,
                            'partner_id': line.partner_id.id,
                            'debit': line.income_tax,
                            'credit': 0,
                            'name': f"{line.partner_id.name} - Income Tax"
                        }),
                        # Income tax credit (3320)
                        (0, 0, {
                            'account_id': account_3320.id,
                            'partner_id': line.partner_id.id,
                            'debit': 0,
                            'credit': line.income_tax,
                            'name': f"{line.partner_id.name} - Income Tax Liability"
                        })
                    ])
                
                # Now create the journal entry with all lines
                move = self.env['account.move'].create({
                    'ref': f"Insurance for {line.partner_id.name}",
                    'date': self.date,
                    'journal_id': journal.id,
                    'line_ids': move_lines
                })
                
                # Verify entry is balanced
                move_debit = sum(move.line_ids.mapped('debit'))
                move_credit = sum(move.line_ids.mapped('credit'))
                _logger.info(f"Entry for {line.partner_id.name}: Debit={move_debit}, Credit={move_credit}")
                
                journal_entries += move
                
            except Exception as e:
                _logger.error(f"Error creating journal entry for {line.partner_id.name}: {e}")
                raise UserError(_(f"Error creating journal entry for {line.partner_id.name}: {e}"))
        
        # Link journal entries to insurance import record
        self.write({
            'journal_entry_ids': [(6, 0, journal_entries.ids)],
            'state': 'posted'
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(f"{len(journal_entries)} journal entries have been generated."),
                'sticky': False,
                'type': 'success',
            }
        }


class InsuranceImportLine(models.Model):
    _name = 'insurance.import.line'
    _description = 'Insurance Import Line'

    import_id = fields.Many2one('insurance.import', string='Insurance Import', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Employee')
    partner_vat = fields.Char(string='ID Number')
    full_name = fields.Char(string='Full Name')
    base_salary = fields.Float(string='Base Salary')
    total_salary = fields.Float(string='Total Salary')
    pension = fields.Float(string='Pension (2%)')
    company_tax = fields.Float(string='Company Tax')
    income_tax = fields.Float(string='Income Tax')
    net_amount = fields.Float(string='Net Amount')
    state = fields.Selection(related='import_id.state', string='Status', store=True)
    company_id = fields.Many2one(related='import_id.company_id', string='Company', store=True)
    
    @api.model
    def search_pension_records(self, min_value=0):
        """
        Search for insurance import lines with pension values above a minimum threshold
        
        Args:
            min_value (float): Minimum pension value to search for
            
        Returns:
            recordset: Insurance import lines with pension > min_value
        """
        return self.search([('pension', '>', min_value)])
    
    def get_pension_stats(self):
        """
        Get statistics about pension contributions
        
        Returns:
            dict: Dictionary with pension statistics
        """
        pension_lines = self.search_pension_records()
        total_pension = sum(pension_lines.mapped('pension'))
        avg_pension = total_pension / len(pension_lines) if pension_lines else 0
        
        return {
            'count': len(pension_lines),
            'total_amount': total_pension,
            'average_amount': avg_pension,
            'min_amount': min(pension_lines.mapped('pension')) if pension_lines else 0,
            'max_amount': max(pension_lines.mapped('pension')) if pension_lines else 0,
        }