from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import pandas as pd
import io
import logging
import traceback
import mimetypes

_logger = logging.getLogger(__name__)

class SalaryImport(models.Model):
    _name = 'salary.import'
    _description = 'Salary Import'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, default='New')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    excel_file = fields.Binary(string='Excel File', required=True)
    excel_filename = fields.Char(string='File Name')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('imported', 'Imported'),
        ('posted', 'Posted')
    ], string='Status', default='draft', copy=False)
    line_ids = fields.One2many('salary.import.line', 'import_id', string='Salary Lines')
    journal_entry_count = fields.Integer(compute='_compute_journal_entry_count')
    journal_entry_ids = fields.Many2many('account.move', string='Journal Entries', copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    def _compute_journal_entry_count(self):
        for record in self:
            record.journal_entry_count = len(record.journal_entry_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('salary.import') or 'New'
        return super(SalaryImport, self).create(vals)
    
    def _validate_excel_file(self, excel_data, filename):
        """
        Validate Excel file before processing
        """
        # Check file size
        if len(excel_data) == 0:
            raise UserError("The uploaded file is empty.")
        
        # Check file type
        if filename:
            mime_type, _ = mimetypes.guess_type(filename)
            valid_types = [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
                'application/vnd.ms-excel',  # .xls
            ]
            if mime_type not in valid_types:
                raise UserError(f"Invalid file type. Please upload an Excel file. Detected type: {mime_type}")
        
        return True
    
    def action_import_excel(self):
        for record in self:
            if not record.excel_file:
                raise UserError("Please upload an Excel file.")
            
            # Decode the file
            try:
                excel_data = base64.b64decode(record.excel_file)
            except Exception as e:
                _logger.error(f"Base64 Decoding Error: {str(e)}")
                raise UserError("Error decoding the uploaded file. Please check the file and try again.")
            
            # Validate file
            self._validate_excel_file(excel_data, record.excel_filename)
            
            # Prepare file for reading
            file_buffer = io.BytesIO(excel_data)
            
            # Try reading with multiple approaches
            try:
                # First, try with openpyxl (recommended for .xlsx)
                df = pd.read_excel(
                    file_buffer, 
                    engine='openpyxl', 
                    skiprows=2,  # Skip first two rows if they are headers
                    dtype=str  # Read all columns as strings to avoid type conversion issues
                )
            except Exception as first_error:
                try:
                    # Fallback to xlrd for older .xls files
                    file_buffer.seek(0)  # Reset buffer
                    df = pd.read_excel(
                        file_buffer, 
                        engine='xlrd', 
                        skiprows=2,
                        dtype=str
                    )
                except Exception as second_error:
                    # Log both errors for debugging
                    _logger.error(f"First attempt error: {first_error}")
                    _logger.error(f"Second attempt error: {second_error}")
                    _logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Comprehensive error message
                    raise UserError(
                        "Could not read the Excel file. Possible reasons:\n"
                        "- File is corrupted\n"
                        "- File is in an unsupported format\n"
                        "- File requires password\n"
                        "- Incompatible Excel version"
                    )
            
            # Log file details for debugging
            _logger.info(f"DataFrame Columns: {list(df.columns)}")
            _logger.info(f"DataFrame Shape: {df.shape}")
            _logger.info(f"First 5 rows:\n{df.head()}")
            
            # Clear existing lines
            record.line_ids.unlink()
            
            # CORRECTED: Define column positions based on the actual Excel structure
            # Based on the Excel screenshot, the correct column mapping is:
            # Column A (0): Row number - skip this
            # Column B (1): პირადი ნომერი (ID Number)
            # Column C (2): სახელი, გვარი (Full Name)
            # Column D (3): ძირითადი ხელფასი (Base Salary)
            # Column E (4): Empty
            # Column F (5): Empty
            # Column G (6): დარიცხული ხელფასი (Total Salary) ✅
            # Column H (7): საპენსიო 2% (Pension) ✅
            # Column I (8): Company Tax (if any)
            # Column J (9): დასაბეგრი 20%-ით (Taxable amount)
            # Column K (10): საშემოსავლო (Income Tax) ✅
            # Column L (11): ხელზე ასაღები (Net Amount) ✅
            
            # Ensure we have enough columns
            if len(df.columns) < 12:
                raise UserError(f"Excel file must have at least 12 columns. Found {len(df.columns)} columns.")
            
            columns_map = {
                'partner_id': df.columns[1],      # Column B: პირადი ნომერი
                'full_name': df.columns[2],        # Column C: სახელი, გვარი
                'base_salary': df.columns[3],      # Column D: ძირითადი ხელფასი
                'total_salary': df.columns[6],     # Column G: დარიცხული ხელფასი ✅
                'pension': df.columns[7],          # Column H: საპენსიო 2% ✅
                'company_tax': df.columns[8],      # Column I: კომპანიის გადასახადი
                'income_tax': df.columns[10],      # Column K: საშემოსავლო ✅
                'net_amount': df.columns[11]       # Column L: ხელზე ასაღები ✅
            }
            
            # Safe float conversion
            def safe_float(val):
                try:
                    if pd.isna(val):
                        return 0.0
                    # Remove non-numeric characters but keep digits, dots, and minus signs
                    if isinstance(val, str):
                        val = ''.join(c for c in val if c.isdigit() or c == '.' or c == '-')
                    return float(val) if val else 0.0
                except:
                    return 0.0
            
            # Prepare lines for batch creation
            import_lines = []
            
            for idx, row in df.iterrows():
                # Skip rows with NaN or empty partner ID
                if pd.isna(row[columns_map['partner_id']]):
                    continue
                
                # Clean the identification number 
                vat = str(row[columns_map['partner_id']]).split('.')[0].zfill(11)
                partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)
                
                # Extract values and log for debugging
                base_salary_val = safe_float(row[columns_map['base_salary']])
                total_salary_val = safe_float(row[columns_map['total_salary']])
                pension_val = safe_float(row[columns_map['pension']])
                company_tax_val = safe_float(row[columns_map['company_tax']])
                income_tax_val = safe_float(row[columns_map['income_tax']])
                net_amount_val = safe_float(row[columns_map['net_amount']])
                
                # Log for debugging
                _logger.info(f"Row {idx}: VAT={vat}, Total Salary={total_salary_val}, Income Tax={income_tax_val}")
                
                # Prepare line values
                line_vals = {
                    'import_id': record.id,
                    'partner_id': partner.id if partner else False,
                    'partner_vat': vat,
                    'full_name': str(row[columns_map['full_name']]),
                    'base_salary': base_salary_val,
                    'total_salary': total_salary_val,
                    'pension': pension_val,
                    'company_tax': company_tax_val,
                    'income_tax': income_tax_val,
                    'net_amount': net_amount_val
                }
                
                # Only add if a partner is found
                if partner:
                    import_lines.append(line_vals)
                else:
                    _logger.warning(f"Partner not found for VAT: {vat}")
            
            # Batch create lines
            if import_lines:
                self.env['salary.import.line'].create(import_lines)
            
            # Update state
            record.state = 'imported'
            
            # Log import details
            _logger.info(f"Imported {len(import_lines)} salary lines")
        
        return True

    def action_generate_journal_entries(self):
        for record in self:
            # Function to find account with fallback methods
            def find_account(code, name=None):
                # Try finding by code without company filter
                account = self.env['account.account'].search([
                    ('code', '=', code)
                ], limit=1)
                
                # If still not found and name is provided, create the account
                if not account and name:
                    try:
                        account = self.env['account.account'].create({
                            'name': name,
                            'code': code,
                            'account_type': 'liability_current',  # Adjust account type as needed
                        })
                    except Exception as e:
                        _logger.error(f"Error creating account {code}: {e}")
                        raise UserError(f"Could not create account {code}: {e}")
                
                return account
            
            # Find accounts 
            accounts = {
                '7410': find_account('7410', 'Salary Expense Account'),
                '3130': find_account('3130', 'Salary Payable Account'),
                '3370': find_account('3370', 'General Liability Account'),
                '7415': find_account('7415', 'Company Tax Expense Account'),
                '3320': find_account('3320', 'Income Tax Liability Account')
            }
            
            # Get general journal
            journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
            
            # Verify accounts and journal exist
            missing_accounts = [code for code, account in accounts.items() if not account]
            if missing_accounts or not journal:
                missing = missing_accounts + (['General Journal'] if not journal else [])
                raise UserError(f"Required accounts or journal not found: {', '.join(missing)}")
            
            # Prepare journal entries
            journal_entries = self.env['account.move']
            
            # Process each line
            for line in record.line_ids:
                if not line.partner_id:
                    continue
                
                try:
                    # Create a single journal entry with all line items
                    move_lines = []
                    
                    # 1. Main salary entry
                    move_lines.extend([
                        # Salary expense debit (7410)
                        (0, 0, {
                            'account_id': accounts['7410'].id,
                            'partner_id': line.partner_id.id,
                            'debit': line.total_salary,
                            'credit': 0,
                            'name': f"{line.partner_id.name} - Salary Expense"
                        }),
                        # Salary credit (3130)
                        (0, 0, {
                            'account_id': accounts['3130'].id,
                            'partner_id': line.partner_id.id,
                            'debit': 0,
                            'credit': line.total_salary,
                            'name': f"{line.partner_id.name} - Salary Payable"
                        })
                    ])
                    
                    # 2. Pension entries if applicable
                    if line.pension > 0:
                        move_lines.extend([
                            # Pension debit (3130)
                            (0, 0, {
                                'account_id': accounts['3130'].id,
                                'partner_id': line.partner_id.id,
                                'debit': line.pension,
                                'credit': 0,
                                'name': f"{line.partner_id.name} - Pension"
                            }),
                            # Pension credit (3370)
                            (0, 0, {
                                'account_id': accounts['3370'].id,
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
                                'account_id': accounts['7415'].id,
                                'partner_id': line.partner_id.id,
                                'debit': line.company_tax,
                                'credit': 0,
                                'name': f"{line.partner_id.name} - Company Tax"
                            }),
                            # Company tax credit (3370)
                            (0, 0, {
                                'account_id': accounts['3370'].id,
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
                                'account_id': accounts['3130'].id,
                                'partner_id': line.partner_id.id,
                                'debit': line.income_tax,
                                'credit': 0,
                                'name': f"{line.partner_id.name} - Income Tax"
                            }),
                            # Income tax credit (3320)
                            (0, 0, {
                                'account_id': accounts['3320'].id,
                                'partner_id': line.partner_id.id,
                                'debit': 0,
                                'credit': line.income_tax,
                                'name': f"{line.partner_id.name} - Income Tax Liability"
                            })
                        ])
                    
                    # Create the journal entry
                    move = self.env['account.move'].create({
                        'ref': f"Salary for {line.partner_id.name}",
                        'date': record.date,
                        'journal_id': journal.id,
                        'line_ids': move_lines
                    })
                    
                    journal_entries += move
                    
                except Exception as e:
                    _logger.error(f"Error creating journal entry for {line.partner_id.name}: {e}")
                    raise UserError(f"Error creating journal entry for {line.partner_id.name}: {e}")
            
            # Link journal entries to salary import record
            record.journal_entry_ids = journal_entries
            record.state = 'posted'
            
            return True

    def action_view_journal_entries(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.journal_entry_ids.ids)]
        }


class SalaryImportLine(models.Model):
    _name = 'salary.import.line'
    _description = 'Salary Import Line'

    import_id = fields.Many2one('salary.import', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Employee')
    partner_vat = fields.Char(string='ID Number')
    full_name = fields.Char(string='Full Name')
    base_salary = fields.Float(string='Base Salary')
    total_salary = fields.Float(string='Total Salary')
    pension = fields.Float(string='Pension (2%)')
    company_tax = fields.Float(string='Company Tax')
    income_tax = fields.Float(string='Income Tax')
    net_amount = fields.Float(string='Net Amount')
    state = fields.Selection(related='import_id.state', store=True)
    company_id = fields.Many2one(related='import_id.company_id', store=True)