from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import logging

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

_logger = logging.getLogger(__name__)

class SalaryPaymentImport(models.Model):
    _name = 'salary.payment.import'
    _description = 'Salary Payment Import'
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
    line_ids = fields.One2many('salary.payment.import.line', 'import_id', string='Payment Lines')
    journal_entry_count = fields.Integer(compute='_compute_journal_entry_count')
    journal_entry_ids = fields.Many2many('account.move', string='Journal Entries', copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    def _compute_journal_entry_count(self):
        for record in self:
            record.journal_entry_count = len(record.journal_entry_ids)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('salary.payment.import') or 'New'
        return super().create(vals_list)
    
    def action_import_excel(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))
        
        if not HAS_PANDAS:
            raise UserError(_("Excel import feature is not available. Please contact your system administrator to install the required components."))
        
        try:
            excel_data = base64.b64decode(self.excel_file)
        except Exception as e:
            raise UserError(_("Failed to decode Excel file: %s") % str(e))
        
        # Read Excel file
        try:
            df = pd.read_excel(io.BytesIO(excel_data), header=None, dtype=str)
        except Exception as e:
            raise UserError(_("Could not read Excel file: %s") % str(e))
        
        if df is None or df.empty:
            raise UserError(_("Excel file is empty or could not be read."))
        
        # Clear existing lines
        self.line_ids.unlink()
        
        # Process rows starting from row 1 (skip headers)
        total_processed = 0
        
        for row_idx in range(1, len(df)):
            try:
                row_data = df.iloc[row_idx]
                
                # Extract values from columns (A, B, C, D, E, F)
                partner_id_str = self._safe_string(row_data.iloc[0]) if len(row_data) > 0 else ''
                amount_str = self._safe_string(row_data.iloc[1]) if len(row_data) > 1 else ''
                debit_str = self._safe_string(row_data.iloc[2]) if len(row_data) > 2 else ''
                credit_str = self._safe_string(row_data.iloc[3]) if len(row_data) > 3 else ''
                credit_partner_str = self._safe_string(row_data.iloc[4]) if len(row_data) > 4 else ''
                project_str = self._safe_string(row_data.iloc[5]) if len(row_data) > 5 else ''  # Column F - PROJECT
                
                # Fix: If Column D is empty but Column C has value, use Column C for credit
                if not credit_str and debit_str:
                    credit_str = debit_str
                
                net_amount = self._safe_float(amount_str)
                
                # Skip empty rows
                if not partner_id_str and net_amount <= 0:
                    continue
                
                # Find or create partner for Column A
                partner = None
                if partner_id_str:
                    partner = self._find_partner_by_id(partner_id_str)
                    if not partner:
                        try:
                            partner = self.env['res.partner'].create({
                                'name': 'Employee %s' % partner_id_str,
                                'vat': partner_id_str.split('.')[0].zfill(11),
                                'is_company': False,
                                'supplier_rank': 1,
                                'customer_rank': 1
                            })
                        except Exception:
                            continue
                
                # Find credit partner for Column E
                credit_partner_obj = None
                if credit_partner_str:
                    credit_partner_obj = self._find_partner_by_name(credit_partner_str)
                
                # Find project/analytic account for Column F
                analytic_account = None
                if project_str:
                    _logger.info(f"Processing project: {project_str}")
                    # First try to find by name
                    analytic_account = self.env['account.analytic.account'].search([
                        ('name', 'ilike', project_str)
                    ], limit=1)
                    
                    # If not found, try by code
                    if not analytic_account:
                        analytic_account = self.env['account.analytic.account'].search([
                            ('code', 'ilike', project_str)
                        ], limit=1)
                    
                    if analytic_account:
                        _logger.info(f"Found analytic account: {analytic_account.name} ({analytic_account.code})")
                    else:
                        _logger.warning(f"No analytic account found for: {project_str}")
                
                # Create line with all data including project
                line_vals = {
                    'import_id': self.id,
                    'partner_name': partner_id_str,
                    'net_amount': net_amount,
                    'debit': debit_str,
                    'credit': credit_str,
                    'credit_partner': credit_partner_str,
                    'project_name': project_str,  # Store project name from Column F
                    'row_number': total_processed + 1,
                    'excel_row': row_idx + 1,
                }
                
                # Add partner references if found
                if partner:
                    line_vals['partner_id'] = partner.id
                if credit_partner_obj:
                    line_vals['credit_partner_id'] = credit_partner_obj.id
                if analytic_account:
                    line_vals['analytic_account_id'] = analytic_account.id
                
                self.env['salary.payment.import.line'].create(line_vals)
                total_processed += 1
                
            except Exception as e:
                _logger.error("Error processing row %s: %s" % (row_idx, str(e)))
                continue
        
        if total_processed == 0:
            raise UserError(_("No data was imported. Please check your Excel file format."))
        
        self.state = 'imported'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Imported %d lines successfully!') % total_processed,
                'type': 'success',
            }
        }
    
    def _safe_string(self, val):
        """Convert value to string safely"""
        try:
            if pd.isna(val) or val is None:
                return ''
            if str(val).lower() == 'nan':
                return ''
            return str(val).strip()
        except:
            return ''
    
    def _safe_float(self, val):
        """Convert value to float safely"""
        try:
            if pd.isna(val) or val == '' or val is None:
                return 0.0
            val_str = str(val).strip()
            if not val_str:
                return 0.0
            # Remove non-numeric characters but keep digits, dots, and minus signs
            cleaned = ''.join(c for c in val_str if c.isdigit() or c in '.-')
            if not cleaned or cleaned == '.' or cleaned == '-':
                return 0.0
            return float(cleaned)
        except:
            return 0.0
    
    def _find_partner_by_id(self, partner_id_str):
        """Find partner by VAT/ID number"""
        if not partner_id_str:
            return False
        
        # Clean and format ID number
        clean_id = partner_id_str.split('.')[0].zfill(11)
        
        # Search by VAT
        partner = self.env['res.partner'].search([('vat', '=', clean_id)], limit=1)
        if partner:
            return partner
        
        # Fallback search with original string
        partner = self.env['res.partner'].search([('vat', '=', partner_id_str)], limit=1)
        return partner
    
    def _find_partner_by_name(self, partner_name):
        """Find partner by name with multiple search strategies"""
        if not partner_name:
            return False
        
        clean_name = partner_name.strip()
        
        # Try different search strategies
        search_strategies = [
            [('name', '=', clean_name)],           # Exact match
            [('name', '=ilike', clean_name)],      # Case insensitive exact
            [('name', 'ilike', "%%%s%%" % clean_name)], # Contains
        ]
        
        for domain in search_strategies:
            partners = self.env['res.partner'].search(domain, limit=1)
            if partners:
                return partners
        
        # Create new partner if not found
        try:
            new_partner = self.env['res.partner'].create({
                'name': clean_name,
                'is_company': False,
                'supplier_rank': 1,
                'customer_rank': 1
            })
            return new_partner
        except:
            return False
    
    def action_generate_journal_entries(self):
        self.ensure_one()
        
        if self.state == 'posted':
            raise UserError(_("Journal entries already generated!"))
        
        if not self.line_ids:
            raise UserError(_("No lines to process!"))
        
        # Get general journal
        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if not journal:
            raise UserError(_("General journal not found!"))
        
        journal_entries = self.env['account.move']
        counter = 1
        successful_entries = 0
        
        # Process each line individually
        for line in self.line_ids:
            try:
                # Must have partner for debit
                if not line.partner_id:
                    counter += 1
                    continue
                
                # Must have amount
                if line.net_amount <= 0:
                    counter += 1
                    continue
                
                amount = line.net_amount
                
                # GET DEBIT ACCOUNT FROM COLUMN C
                debit_account = None
                if line.debit and line.debit.strip():
                    debit_account = self.env['account.account'].search([('code', '=', line.debit.strip())], limit=1)
                    if not debit_account:
                        # Create account if doesn't exist
                        try:
                            debit_account = self.env['account.account'].create({
                                'name': 'Account %s' % line.debit.strip(),
                                'code': line.debit.strip(),
                                'account_type': 'liability_current',
                            })
                        except Exception as e:
                            _logger.error("Cannot create debit account %s: %s" % (line.debit.strip(), str(e)))
                            counter += 1
                            continue
                
                # GET CREDIT ACCOUNT FROM COLUMN D OR E
                credit_account = None
                credit_partner_for_entry = None
                
                # Priority 1: If Column E has partner, use their payable account
                if line.credit_partner_id:
                    credit_account = line.credit_partner_id.property_account_payable_id
                    credit_partner_for_entry = line.credit_partner_id
                    _logger.info("Using credit partner %s with account %s" % (line.credit_partner_id.name, credit_account.code if credit_account else 'None'))
                
                # Priority 2: If Column D has account code, use that account
                elif line.credit and line.credit.strip():
                    credit_account = self.env['account.account'].search([('code', '=', line.credit.strip())], limit=1)
                    if not credit_account:
                        # Create account if doesn't exist
                        try:
                            credit_account = self.env['account.account'].create({
                                'name': 'Account %s' % line.credit.strip(),
                                'code': line.credit.strip(),
                                'account_type': 'liability_current',
                            })
                        except Exception as e:
                            _logger.error("Cannot create credit account %s: %s" % (line.credit.strip(), str(e)))
                            counter += 1
                            continue
                    credit_partner_for_entry = None
                    _logger.info("Using credit account %s without partner" % credit_account.code)
                
                # Priority 3: Fallback to debit partner's payable account
                else:
                    credit_account = line.partner_id.property_account_payable_id
                    credit_partner_for_entry = line.partner_id
                    _logger.info("Using debit partner %s payable account as fallback" % line.partner_id.name)
                
                # Must have both accounts
                if not debit_account or not credit_account:
                    _logger.warning("Missing accounts - Debit: %s, Credit: %s" % (debit_account, credit_account))
                    counter += 1
                    continue
                
                # Prepare analytic distribution for project (ONLY for debit line)
                analytic_distribution = {}
                if line.analytic_account_id:
                    analytic_distribution[str(line.analytic_account_id.id)] = 100.0
                    _logger.info(f"Analytic distribution created: {analytic_distribution}")
                else:
                    _logger.info("No analytic account found for line")
                
                # Ensure analytic distribution is properly formatted for both lines
                if analytic_distribution:
                    analytic_distribution_debit = analytic_distribution.copy()
                    analytic_distribution_credit = analytic_distribution.copy()
                else:
                    analytic_distribution_debit = False
                    analytic_distribution_credit = False
                
                # Check if debit partner is a company
                is_company_partner = line.partner_id.is_company if line.partner_id else False
                _logger.info(f"Partner: {line.partner_id.name}, is_company: {is_company_partner}")
                _logger.info(f"Project name: {line.project_name}, Analytic account: {line.analytic_account_id.name if line.analytic_account_id else 'None'}")
                
                # Create journal entry with project support
                move_vals = {
                    'journal_id': journal.id,
                    'date': self.date,
                    'ref': _("Payment %d - %s - %.2f GEL%s") % (
                        counter, 
                        line.partner_id.name, 
                        amount,
                        " - Project: %s" % line.project_name if line.project_name else ""
                    ),
                    'line_ids': [
                        # Debit line (Column C account + Column A partner + Project)
                        (0, 0, {
                            'account_id': debit_account.id,
                            'partner_id': line.partner_id.id,
                            'analytic_distribution': analytic_distribution_debit,  # Analytic on debit
                            'debit': amount,
                            'credit': 0.0,
                            'name': _('Payment Debit - %s%s') % (
                                line.partner_id.name,
                                " - Project: %s" % line.project_name if line.project_name else ""
                            )
                        }),
                        # Credit line (Column D account or Column E partner + Project)
                        # For company partners, credit line should not have partner
                        (0, 0, {
                            'account_id': credit_account.id,
                            'partner_id': None if is_company_partner else (credit_partner_for_entry.id if credit_partner_for_entry else None),
                            'analytic_distribution': False,  # NO analytic on credit line
                            'debit': 0.0,
                            'credit': amount,
                            'name': _('Payment Credit - %s%s') % (
                                credit_partner_for_entry.name if credit_partner_for_entry and not is_company_partner else f'Account {credit_account.code}',
                                " - Project: %s" % line.project_name if line.project_name else ""
                            )
                        })
                    ]
                }
                
                # Create the journal entry
                move = self.env['account.move'].create(move_vals)
                journal_entries += move
                successful_entries += 1
                
                _logger.info("Created journal entry %s: Debit %s / Credit %s for %s - Project: %s - Company Partner: %s - Analytic: %s" % (counter, debit_account.code, credit_account.code, amount, line.project_name or 'N/A', is_company_partner, analytic_distribution))
                
            except Exception as e:
                _logger.error("Error creating journal entry for line %s: %s" % (counter, str(e)))
                pass
            
            counter += 1
        
        # Update state and link journal entries
        self.write({
            'journal_entry_ids': [(6, 0, journal_entries.ids)],
            'state': 'posted'
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%d journal entries created successfully!') % successful_entries,
                'type': 'success',
            }
        }
    
    def action_view_journal_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.journal_entry_ids.ids)]
        }


class SalaryPaymentImportLine(models.Model):
    _name = 'salary.payment.import.line'
    _description = 'Salary Payment Import Line'

    import_id = fields.Many2one('salary.payment.import', required=True, ondelete='cascade')
    partner_name = fields.Char(string='A სვეტი - პირადი ნომერი')
    partner_id = fields.Many2one('res.partner', string='დებიტის პარტნიორი (A)')
    net_amount = fields.Float(string='თანხა (B)')
    debit = fields.Char(string='დებიტი (C)')
    credit = fields.Char(string='კრედიტი (D)')
    credit_partner = fields.Char(string='E სვეტი - კრედიტის პარტნიორის სახელი')
    credit_partner_id = fields.Many2one('res.partner', string='კრედიტის პარტნიორი (E)')
    project_name = fields.Char(string='F სვეტი - PROJECT')
    analytic_account_id = fields.Many2one('account.analytic.account', string='პროექტი/Analytic Account')
    row_number = fields.Integer(string='Line Number')
    excel_row = fields.Integer(string='Excel Row')
    state = fields.Selection(related='import_id.state', store=True)
    company_id = fields.Many2one(related='import_id.company_id', store=True)