from odoo import models, fields, api, _, Command
from odoo.exceptions import UserError, ValidationError
import logging
import re
from dateutil.relativedelta import relativedelta
from datetime import datetime

_logger = logging.getLogger(__name__)


def _analytic_distribution_from_label(env, label):
    """Extract first word from label, match to account.analytic.account.code."""
    if not label:
        return None
    first_word = label.strip().split()[0].strip(';,. ') if label.strip() else ''
    if not first_word:
        return None
    account = env['account.analytic.account'].search([('code', '=', first_word)], limit=1)
    if account:
        _logger.info("Analytic match: label first word '%s' → analytic account %s (%s)", first_word, account.id, account.name)
        return {str(account.id): 100.0}
    return None




# ============================================================================
# CORE MODELS - Keep existing class names
# ============================================================================

class TBCCodeMapping(models.Model):
    """TBC Code Mapping for Account Generation"""
    _name = 'tbc.code.mapping'
    _description = 'TBC Code Mapping for Account Generation'
    _rec_name = 'code_field'

    code_field = fields.Char(string='Code', required=True, index=True)
    comment = fields.Text(
        string='Comment Keywords',
        help='Enter keywords separated by commas to search in comments (e.g., ხელფასი, პრემია, ბონუსი)'
    )
    debit_credit = fields.Selection([
        ('debit', 'Debit'),
        ('credit', 'Credit')
    ], string='Debit/Credit', required=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    partner_required = fields.Selection([
        ('yes', 'Yes - Partner Required'),
        ('no', 'No - Partner Not Required')
    ], string='Partner Finding Required', required=True, default='yes',
        help='Determines if partner finding is mandatory for this mapping')

    # NEW: Link to reconcile models that use this mapping
    reconcile_model_ids = fields.Many2many(
        'account.reconcile.model',
        string='Reconciliation Models',
        help='Reconciliation models using this TBC mapping'
    )


class CustomBank(models.Model):
    """Bank Type - KEPT AS IS"""
    _name = 'custom.bank'
    _description = 'Bank Type'

    name = fields.Char(string='Bank Name', required=True)


class AccountAccount(models.Model):
    """Extend Account with Bank Type - KEPT AS IS"""
    _inherit = 'account.account'

    bank_type_id = fields.Many2one('custom.bank', string='Bank Type')


class ResUsersExtended(models.Model):
    """Extended User with BOG credentials - KEPT AS IS"""
    _inherit = 'res.users'

    bog_client_secret = fields.Char(string='BOG Client Secret')
    bog_client_id = fields.Char(string='BOG Client ID')


# ============================================================================
# TBC TRANSACTION MODEL - Reworked to create bank statement lines
# ============================================================================

class TBCPaymentIntegration(models.Model):
    """TBC Transaction Model - Reworked for standard Odoo reconciliation"""
    _name = 'tbc_payment_integration.tbc_payment_integration'
    _description = 'TBC Payment Integration'
    _order = 'entry_date desc, id desc'

    # Transaction Data Fields - Keep field names
    entry_date = fields.Date(string="შეყვანის თარიღი", index=True)
    entry_document_number = fields.Char(string="დოკუმენტის ნომერი", index=True)
    entry_account_number = fields.Char(string="შეყვანილი ბანკის ანგარიში")
    entry_amount_debit = fields.Float(string="დებეტის თანხა")
    entry_amount_debit_base = fields.Float(string="ძირითადი დებეტის თანხა")
    entry_amount_credit = fields.Float(string="კრედიტის თანხა")
    entry_amount_credit_base = fields.Float(string="ძირითადი კრედიტის თანხა")
    entry_amount_base = fields.Float(string="ძირითადი თანხა")
    entry_amount = fields.Float(string="შეყვანილი თანხა")
    entry_comment = fields.Text(string="კომენტარი")
    entry_department = fields.Char(string="შეყვანილი დეპარტამენტი")
    entry_account_point = fields.Char(string="ანგარიშის წერტილი")

    document_product_group = fields.Char(string="დოკუმენტის პროდუქტის ჯგუფი", index=True)
    document_product_group_mapping = fields.Many2one(
        'tbc.code.mapping',
        string='Product Group Mapping',
        compute='_compute_product_group_mapping',
        store=True
    )
    document_value_date = fields.Date(string="დოკუმენტის ღირებულების თარიღი")

    # Sender Details
    sender_details_name = fields.Char(string="გამგზავნის სახელი")
    sender_details_inn = fields.Char(string="გამგზავნის საიდენტიფიკაციო ნომერი", index=True)
    sender_details_account_number = fields.Char(string="ბანკის ანგარიში")
    sender_details_bank_code = fields.Char(string="ბანკის კოდი")
    sender_details_bank_name = fields.Char(string="ბანკის სახელი")

    # Beneficiary Details
    beneficiary_details_name = fields.Char(string="ბენეფიციარის სახელი")
    beneficiary_details_inn = fields.Char(string="ბენეფიციარის საიდენტიფიკაციო ნომერი", index=True)
    beneficiary_details_account_number = fields.Char(string="ბენეფიციარის ბანკის ანგარიში")
    beneficiary_details_bank_code = fields.Char(string="ბენეფიციარის ბანკის კოდი")
    beneficiary_details_bank_name = fields.Char(string="ბენეფიციარის ბანკის სახელი")

    # Additional Document Fields
    document_treasury_code = fields.Char(string="დოკუმენტის ხაზინარი კოდი")
    document_nomination = fields.Char(string="დოკუმენტის ნომინაცია")
    document_information = fields.Text(string="დოკუმენტის ინფორმაცია")
    document_source_amount = fields.Float(string="დოკუმენტის წყაროს თანხა")
    document_source_currency = fields.Char(string="დოკუმენტის წყაროს ვალუტა")
    document_destination_amount = fields.Float(string="დოკუმენტის დანიშნულების თანხა")
    document_destination_currency = fields.Char(string="დოკუმენტის დანიშნულების ვალუტა")
    document_receive_date = fields.Date(string="დოკუმენტის მიღების თარიღი")
    document_branch = fields.Char(string="დოკუმენტის ფილიალი")
    document_department = fields.Char(string="დოკუმენტის დეპარტამენტი")
    document_actual_date = fields.Date(string="დოკუმენტის რეალური თარიღი")
    document_expiry_date = fields.Date(string="დოკუმენტის ვადის გასვლის თარიღი")
    document_rate_limit = fields.Float(string="დოკუმენტის საპროცენტო საზღვარი")
    document_rate = fields.Float(string="დოკუმენტის განაკვეთი")
    document_registration_rate = fields.Float(string="დოკუმენტის რეგისტრაციის განაკვეთი")
    document_sender_institution = fields.Char(string="დოკუმენტის გამგზავნის ინსტიტუტი")
    document_intermediary_institution = fields.Char(string="დოკუმენტის შუამავალი ინსტიტუტი")
    document_beneficiary_institution = fields.Char(string="დოკუმენტის ბენეფიციარის ინსტიტუტი")
    document_payee = fields.Char(string="დოკუმენტის მიმღები")
    document_correspondent_account_number = fields.Char(string="დოკუმენტის კორესპონდენტის ანგარიშის ნომერი")
    document_correspondent_bank_code = fields.Char(string="დოკუმენტის კორესპონდენტის ბანკის კოდი")
    document_correspondent_bank_name = fields.Char(string="დოკუმენტის კორესპონდენტის ბანკის სახელი")
    document_key = fields.Char(string="დოკუმენტის გასაღები", index=True)
    entry_id = fields.Char(string="შეყვანის ID", index=True)
    doc_comment = fields.Text(string="დოკუმენტის კომენტარი")
    document_payer_inn = fields.Char(string="დოკუმენტის გადამხდელის TIN")
    document_payer_name = fields.Char(string="დოკუმენტის გადამხდელის სახელი")
    my_bank_id = fields.Char(string="მითითებული ბანკის ანგარიში")

    # NEW: State management for Odoo-standard flow
    state = fields.Selection([
        ('draft', 'Draft - Not Imported'),
        ('imported', 'Imported - Statement Line Created'),
        ('reconciled', 'Reconciled'),
        ('error', 'Error')
    ], string='Status', default='draft', tracking=True)

    # NEW: Link to created bank statement line
    statement_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Statement Line',
        help='The bank statement line created from this transaction',
        readonly=True
    )

    # NEW: Computed fields for reconciliation info
    is_reconciled = fields.Boolean(
        string='Is Reconciled',
        related='statement_line_id.is_reconciled',
        store=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Detected Partner',
        compute='_compute_partner_id',
        store=True,
        help='Partner detected from INN'
    )

    suggested_mapping_id = fields.Many2one(
        'tbc.code.mapping',
        string='Suggested Mapping',
        compute='_compute_suggested_mapping',
        store=True
    )

    # Legacy fields (keep for compatibility but mark as deprecated)
    payment_id = fields.Many2one(
        'account.payment',
        string='Related Payment (Deprecated)',
        help='Legacy field - not used in new flow'
    )
    related_journal_entry_id = fields.Many2one(
        'account.move',
        string='Related Journal Entry (Deprecated)',
        help='Legacy field - not used in new flow'
    )

    @api.depends('document_product_group')
    def _compute_product_group_mapping(self):
        """Compute the mapping based on product group"""
        for record in self:
            if record.document_product_group:
                mapping = self.env['tbc.code.mapping'].search([
                    ('code_field', '=', record.document_product_group)
                ], limit=1)
                record.document_product_group_mapping = mapping
            else:
                record.document_product_group_mapping = False

    @api.depends('sender_details_inn', 'beneficiary_details_inn', 'sender_details_name', 'beneficiary_details_name', 'entry_amount_debit', 'entry_amount_credit')
    def _compute_partner_id(self):
        """Auto-detect partner from INN or name"""
        for record in self:
            partner = False
            is_debit = record.entry_amount_debit > 0
            is_credit = record.entry_amount_credit > 0

            # Determine partner details based on transaction type
            # Credit filled (positive statement) → main line partner is BENEFICIARY
            # Debit filled (negative statement) → main line partner is SENDER
            if is_credit:
                # Credit filled = positive = beneficiary is main line partner
                partner_inn = record.beneficiary_details_inn
                partner_name = record.beneficiary_details_name
            else:
                # Debit filled = negative = sender is main line partner
                partner_inn = record.sender_details_inn
                partner_name = record.sender_details_name

            # Step 1: Try to find by VAT (INN) - highest priority
            if partner_inn:
                partner = self.env['res.partner'].search([
                    ('vat', '=', partner_inn)
                ], limit=1)

            # Step 2: If not found by VAT, try by exact name
            if not partner and partner_name:
                partner = self.env['res.partner'].search([
                    ('name', '=', partner_name)
                ], limit=1)

            # Step 3: If still not found, try fuzzy name match
            if not partner and partner_name:
                partner = self.env['res.partner'].search([
                    ('name', '=ilike', partner_name)
                ], limit=1)

            record.partner_id = partner

    @api.depends('document_product_group', 'entry_comment', 'doc_comment', 'entry_amount_debit', 'entry_amount_credit')
    def _compute_suggested_mapping(self):
        """Compute suggested mapping based on TBC logic"""
        for record in self:
            mapping = False
            if record.document_product_group:
                # Use mapping directly: debit field filled = use debit mapping, credit field filled = use credit mapping
                is_credit = record.entry_amount_credit > 0
                transaction_type = 'credit' if is_credit else 'debit'

                # Search for mappings
                all_mappings = self.env['tbc.code.mapping'].search([
                    ('code_field', '=', record.document_product_group)
                ])

                type_filtered = all_mappings.filtered(
                    lambda m: m.debit_credit == transaction_type
                )

                if type_filtered:
                    # Try to match by comment keywords
                    comment_text = (record.entry_comment or '') + ' ' + (record.doc_comment or '')
                    comment_text = comment_text.lower()

                    for map_rec in type_filtered:
                        if map_rec.comment and map_rec.comment.strip():
                            keywords = [kw.strip().lower() for kw in map_rec.comment.split(',')]
                            if any(kw in comment_text for kw in keywords):
                                mapping = map_rec
                                break

                    # Fallback to empty comment mapping or first
                    if not mapping:
                        empty_comment = type_filtered.filtered(lambda m: not m.comment or not m.comment.strip())
                        mapping = empty_comment[0] if empty_comment else type_filtered[0]
                elif all_mappings:
                    mapping = all_mappings[0]

            record.suggested_mapping_id = mapping

    def _get_currency_rate(self, currency_name, transaction_date):
        """
        Get currency rate for converting to GEL from res.currency.rate
        Currency rate is stored in company_rate field, date in name field (Date type)
        Raises UserError if no rate is found for the transaction date
        """
        if not currency_name or currency_name == 'GEL':
            return 1.0

        if not transaction_date:
            raise UserError(
                f"No transaction date provided for currency conversion from {currency_name} to GEL.\n"
                f"Please ensure all transactions have valid dates."
            )

        # Find the currency
        currency = self.env['res.currency'].search([('name', '=', currency_name)], limit=1)
        if not currency:
            raise UserError(
                f"Currency '{currency_name}' not found in the system.\n"
                f"Please add this currency to res.currency before importing transactions."
            )

        # Parse date string to date object
        if isinstance(transaction_date, str):
            # Try multiple date formats
            date_obj = None
            for date_format in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y']:
                try:
                    date_obj = datetime.strptime(transaction_date, date_format)
                    break
                except ValueError:
                    continue

            if not date_obj:
                raise UserError(
                    f"Invalid transaction date format: {transaction_date}\n"
                    f"Expected formats: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or DD/MM/YYYY"
                )
        else:
            date_obj = transaction_date

        formatted_date_display = date_obj.strftime('%d/%m/%Y')  # For display

        # Search for the rate with matching currency and date in name field
        # Note: name field in res.currency.rate is a Date field, so we search with date object
        search_date = date_obj.date() if hasattr(date_obj, 'date') else date_obj
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency.id),
            ('name', '=', search_date)
        ], limit=1)

        if rate_record and rate_record.company_rate:
            _logger.info(f"Found rate for {currency_name} on {formatted_date_display}: {rate_record.company_rate}")
            return float(rate_record.company_rate)
        else:
            # No exact match found - raise error
            raise UserError(
                f"Currency exchange rate not found!\n\n"
                f"Currency: {currency_name}\n"
                f"Date: {formatted_date_display}\n\n"
                f"Please update currency exchange rates in res.currency.rate for the selected dates.\n"
                f"Required format:\n"
                f"  - Currency: {currency_name}\n"
                f"  - Name (date): {formatted_date_display}\n"
                f"  - Company Rate: (e.g., 0.319560285048)"
            )

    def _convert_to_gel(self, amount, currency_name, transaction_date):
        """Convert amount from foreign currency to GEL using res.currency.rate"""
        if not amount or currency_name == 'GEL':
            return amount

        rate = self._get_currency_rate(currency_name, transaction_date)
        converted_amount = amount / rate if rate else amount
        _logger.info(f"Converting {amount} {currency_name} to GEL: {converted_amount} (rate: {rate})")
        return converted_amount

    def action_create_statement_lines(self):
        """
        NEW METHOD: Create bank statement lines from TBC transactions
        This is the main entry point for the new Odoo-standard flow
        """
        created_count = 0
        skipped_count = 0

        for transaction in self:
            if transaction.state == 'imported' and transaction.statement_line_id:
                _logger.info("Transaction %s already has statement line %s, skipping",
                           transaction.id, transaction.statement_line_id.id)
                skipped_count += 1
                continue

            try:
                statement_line = transaction._create_bank_statement_line()
                transaction.write({
                    'statement_line_id': statement_line.id,
                    'state': 'imported'
                })
                _logger.info("Created statement line %s for transaction %s", statement_line.id, transaction.id)
                created_count += 1
            except Exception as e:
                transaction.state = 'error'
                _logger.error("Failed to create statement line for transaction %s: %s", transaction.id, str(e))
                skipped_count += 1
                raise UserError(_('Failed to create statement line: %s') % str(e))

        message = _('%d bank statement lines created successfully') % created_count
        if skipped_count > 0:
            message += _(', %d already imported') % skipped_count

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_bank_statement_line(self, journal=None):
        """
        Create a bank statement line from this TBC transaction
        Args:
            journal: Optional journal to use. If not provided, will auto-detect.
        Returns: account.bank.statement.line record
        """
        self.ensure_one()

        # Check if statement line already exists for this transaction
        if self.statement_line_id:
            _logger.info("Statement line already exists for transaction %s", self.id)
            return self.statement_line_id

        # Determine amount and direction
        is_debit = self.entry_amount_debit > 0
        is_credit = self.entry_amount_credit > 0

        # For BOG: Use base fields (already in GEL) when currency is not GEL
        # For non-GEL transactions, BOG provides GEL equivalent in base fields
        source_currency = self.document_destination_currency or 'GEL'
        if source_currency != 'GEL':
            # Use base fields which contain GEL equivalent
            amount = abs(self.entry_amount_debit) if is_debit else abs(self.entry_amount_credit)
            _logger.info(f"Using base GEL amount for {source_currency} transaction {self.id}: {amount}")
        else:
            # For GEL transactions, use normal amount fields
            amount = abs(self.entry_amount_debit) if is_debit else abs(self.entry_amount_credit)

        # BOG perspective is INVERTED from company perspective:
        # Credit filled in BOG → positive in statement (money OUT from company)
        # Debit filled in BOG → negative in statement (money IN to company)
        signed_amount = amount if is_credit else -amount

        # Find appropriate bank journal (use provided or auto-detect)
        if not journal:
            journal = self._find_bank_journal()
        if not journal:
            raise UserError(_('No bank journal found for account: %s') % self.entry_account_number)

        # Check if a statement line already exists with same document_key and journal
        # Note: journal.id already ensures we're checking the same bank account
        if self.document_key:
            existing_line = self.env['account.bank.statement.line'].search([
                ('journal_id', '=', journal.id),
                ('transaction_details', '!=', False)
            ])
            for line in existing_line:
                if line.transaction_details and isinstance(line.transaction_details, dict):
                    if line.transaction_details.get('document_key') == self.document_key:
                        _logger.warning("Statement line already exists for document_key %s on journal %s, linking to transaction %s",
                                      self.document_key, journal.name, self.id)
                        self.write({
                            'statement_line_id': line.id,
                            'state': 'imported'
                        })
                        return line

        # Prepare payment reference
        payment_ref = self.entry_comment or self.entry_document_number or '/'

        # Determine the correct partner for statement line
        # Credit filled (positive statement) → main line partner is BENEFICIARY
        # Debit filled (negative statement) → main line partner is SENDER
        if is_credit:
            # Credit filled = positive = beneficiary is main line partner
            partner_inn = self.beneficiary_details_inn
            partner_name = self.beneficiary_details_name
        else:
            # Debit filled = negative = sender is main line partner
            partner_inn = self.sender_details_inn
            partner_name = self.sender_details_name

        # Find partner by INN or name
        partner = False
        if partner_inn:
            partner = self.env['res.partner'].search([('vat', '=', partner_inn)], limit=1)
        if not partner and partner_name:
            partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if not partner and partner_name:
            partner = self.env['res.partner'].search([('name', '=ilike', partner_name)], limit=1)

        # Prepare bank statement line values
        # Note: All amounts are now in GEL (converted in wizard), so no foreign_currency_id needed
        vals = {
            'journal_id': journal.id,
            'date': self.entry_date or fields.Date.today(),
            'payment_ref': payment_ref,
            'partner_id': partner.id if partner else False,
            'amount': signed_amount,
            'transaction_type': self.document_product_group,
        }

        # Note: We don't set foreign_currency_id anymore because:
        # 1. All journals use GEL as currency_id
        # 2. Amounts have been converted to GEL in the wizard
        # 3. Currency is only identified by journal name suffix

        # Store TBC transaction details in transaction_details JSON field
        vals['transaction_details'] = {
            'tbc_transaction_id': self.id,
            'document_key': self.document_key,
            'product_group': self.document_product_group,
            'entry_comment': self.entry_comment,  # NEW: For keyword matching
            'doc_comment': self.doc_comment,  # NEW: Additional comment
            'sender_inn': self.sender_details_inn,
            'sender_name': self.sender_details_name,
            'beneficiary_inn': self.beneficiary_details_inn,
            'beneficiary_name': self.beneficiary_details_name,
        }

        # Create statement line
        statement_line = self.env['account.bank.statement.line'].create(vals)

        return statement_line

    def _find_bank_journal(self):
        """
        Find the appropriate bank journal for this transaction
        Journal is identified by currency suffix in name (e.g., GE29BG0000000586405640USD)
        """
        self.ensure_one()

        # Try to find journal by account number and currency
        account_number = self.entry_account_number or self.my_bank_id
        transaction_currency = self.document_source_currency or 'GEL'

        if account_number:
            # Clean account number (remove all currency suffixes)
            clean_account = account_number.replace(' ', '')
            for curr in ['GEL', 'USD', 'EUR', 'RUB', 'GBP']:
                clean_account = clean_account.replace(curr, '')

            # Build journal name with currency suffix
            journal_name_with_currency = f"{clean_account}{transaction_currency}"

            # Get currency record for filtering
            currency_record = self.env['res.currency'].search([('name', '=', transaction_currency)], limit=1)

            # Search for journal with matching name (account + currency suffix) and currency_id
            domain = [
                ('type', '=', 'bank'),
                ('name', '=', journal_name_with_currency)
            ]
            if currency_record:
                domain.append(('currency_id', '=', currency_record.id))

            journal = self.env['account.journal'].search(domain, limit=1)

            if journal:
                _logger.debug(f"Found journal by name with currency: {journal.name}")
                return journal

            # Fallback: Try exact match with original account number and currency filter
            domain = [
                ('type', '=', 'bank'),
                ('name', '=', account_number)
            ]
            if currency_record:
                domain.append(('currency_id', '=', currency_record.id))

            journal = self.env['account.journal'].search(domain, limit=1)

            if journal:
                return journal

            # Try to find by bank_account_id with currency filter
            bank_account = self.env['res.partner.bank'].search([
                '|',
                ('acc_number', '=', account_number),
                ('acc_number', '=', clean_account)
            ], limit=1)

            if bank_account and bank_account.journal_id:
                # Verify currency matches
                if currency_record and bank_account.journal_id.currency_id == currency_record:
                    return bank_account.journal_id
                elif not currency_record:
                    return bank_account.journal_id

        # Fallback to any bank journal with matching currency
        if currency_record:
            return self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('currency_id', '=', currency_record.id)
            ], limit=1)

        return self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

    def action_view_statement_line(self):
        """Open the related bank statement line"""
        self.ensure_one()
        if not self.statement_line_id:
            raise UserError(_('No statement line created yet'))

        return {
            'name': _('Bank Statement Line'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'res_id': self.statement_line_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_reconciliation(self):
        """Open reconciliation widget for this transaction's statement line"""
        self.ensure_one()
        if not self.statement_line_id:
            raise UserError(_('Please create statement line first'))

        # Return action to open bank reconciliation widget
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': {
                'statement_line_ids': [self.statement_line_id.id],
                'company_ids': self.statement_line_id.company_id.ids,
            }
        }

    # LEGACY METHODS - Keep for backward compatibility but mark as deprecated
    def action_process_multiple_transactions(self):
        """DEPRECATED: Use action_create_statement_lines instead"""
        _logger.warning("action_process_multiple_transactions is deprecated. Use action_create_statement_lines instead")
        return self.action_create_statement_lines()

    def action_process_single_transaction(self):
        """DEPRECATED: Use action_create_statement_lines instead"""
        _logger.warning("action_process_single_transaction is deprecated. Use action_create_statement_lines instead")
        return self.action_create_statement_lines()


# ============================================================================
# EXTEND ODOO RECONCILIATION MODEL
# ============================================================================

class AccountReconcileModel(models.Model):
    """Extend Odoo's reconciliation model to support TBC mappings"""
    _inherit = 'account.reconcile.model'

    # NEW: TBC-specific fields
    use_tbc_mapping = fields.Boolean(
        string='Use TBC Code Mapping',
        help='Enable TBC bank code mapping for this reconciliation model'
    )
    tbc_code_mapping_ids = fields.Many2many(
        'tbc.code.mapping',
        string='TBC Code Mappings',
        help='TBC code mappings to use for this reconciliation model'
    )
    tbc_match_product_group = fields.Char(
        string='Match Product Group',
        help='Match transactions with this TBC product group code'
    )

    def _get_invoice_matching_rules_map(self):
        """Override to add TBC-specific matching rules"""
        rules_map = super()._get_invoice_matching_rules_map()

        # Add TBC-specific rule
        if self.use_tbc_mapping:
            # Insert TBC rule at priority 1 (before other rules)
            if 1 not in rules_map:
                rules_map[1] = []
            rules_map[1].append(self._get_tbc_mapping_match)

        return rules_map

    def _get_tbc_mapping_match(self, st_line, partner):
        """
        Custom matching rule based on TBC transaction data
        """
        self.ensure_one()

        # Check if this statement line comes from a TBC transaction
        tbc_transaction_id = st_line.transaction_details.get('tbc_transaction_id') if st_line.transaction_details else False
        if tbc_transaction_id:
            tbc_transaction = self.env['tbc_payment_integration.tbc_payment_integration'].browse(tbc_transaction_id)
            if not tbc_transaction.exists():
                return {}

            # Check product group match
            if self.tbc_match_product_group and tbc_transaction.document_product_group != self.tbc_match_product_group:
                return {}

            # Get suggested mapping
            mapping = tbc_transaction.suggested_mapping_id
            if not mapping:
                return {}

            # Check if partner is required
            if mapping.partner_required == 'yes' and not partner:
                return {}

            # Return match result - will create counterpart with the mapped account
            return {
                'status': 'write_off',
                'auto_reconcile': self.auto_reconcile,
            }

        # NEW: Check if this statement line comes from a TBC movement
        tbc_movement_id = st_line.transaction_details.get('tbc_movement_id') if st_line.transaction_details else False
        if tbc_movement_id:
            tbc_movement = self.env['tbc.movements'].browse(tbc_movement_id)
            if not tbc_movement.exists():
                return {}

            # Check operation code match (similar to product group)
            if self.tbc_match_product_group and tbc_movement.operation_code != self.tbc_match_product_group:
                return {}

            # Get suggested mapping
            mapping = tbc_movement.suggested_mapping_id
            if not mapping:
                return {}

            # Check if partner is required
            if mapping.partner_required == 'yes' and not partner:
                return {}

            # Return match result - will create counterpart with the mapped account
            return {
                'status': 'write_off',
                'auto_reconcile': self.auto_reconcile,
            }

        return {}

    def _apply_lines_for_bank_widget(self, residual_amount_currency, partner, st_line):
        """
        Override to use TBC code mapping when creating counterpart entries
        Uses existing tbc.code.mapping with product_group/operation_code + comment keywords
        """
        # Check if this is a TBC transaction
        tbc_transaction_id = st_line.transaction_details.get('tbc_transaction_id') if st_line.transaction_details else False

        if self.use_tbc_mapping and tbc_transaction_id:
            tbc_transaction = self.env['tbc_payment_integration.tbc_payment_integration'].browse(tbc_transaction_id)

            # Check if record actually exists
            if not tbc_transaction.exists():
                _logger.warning("TBC transaction %s does not exist, falling back to standard behavior", tbc_transaction_id)
                return super()._apply_lines_for_bank_widget(residual_amount_currency, partner, st_line)

            _logger.info("="*80)
            _logger.info("RECONCILIATION WIDGET - Partner Detection Debug")
            _logger.info("Transaction ID: %s", tbc_transaction.id)
            _logger.info("Passed partner parameter: %s (ID: %s, VAT: %s)",
                        partner.name if partner else 'None',
                        partner.id if partner else 'None',
                        partner.vat if partner else 'None')
            _logger.info("Statement line partner: %s (ID: %s)",
                        st_line.partner_id.name if st_line.partner_id else 'None',
                        st_line.partner_id.id if st_line.partner_id else 'None')

            # Use the suggested_mapping which already handles keyword matching
            mapping = tbc_transaction.suggested_mapping_id

            if mapping:
                # Get the correct partner from transaction details, not from the passed parameter
                # Extract partner info from transaction_details JSON
                beneficiary_inn = st_line.transaction_details.get('beneficiary_inn')
                beneficiary_name = st_line.transaction_details.get('beneficiary_name')
                sender_inn = st_line.transaction_details.get('sender_inn')
                sender_name = st_line.transaction_details.get('sender_name')

                _logger.info("Transaction details - Beneficiary: %s (VAT: %s)", beneficiary_name, beneficiary_inn)
                _logger.info("Transaction details - Sender: %s (VAT: %s)", sender_name, sender_inn)
                _logger.info("Transaction amounts - Debit: %s, Credit: %s",
                           tbc_transaction.entry_amount_debit, tbc_transaction.entry_amount_credit)

                # Determine correct partner based on transaction direction
                # Statement line with negative value → counterpart is BENEFICIARY
                # Statement line with positive value → counterpart is SENDER
                is_credit = tbc_transaction.entry_amount_credit > 0
                is_debit = tbc_transaction.entry_amount_debit > 0

                # Credit filled → positive statement, Debit filled → negative statement
                # So: Debit filled → negative → beneficiary counterpart
                #     Credit filled → positive → sender counterpart
                if is_debit:
                    # Debit filled = negative statement = beneficiary is counterpart
                    correct_partner_inn = beneficiary_inn
                    correct_partner_name = beneficiary_name
                    _logger.info("DEBIT FILLED in BOG (negative statement) - COUNTERPART is BENEFICIARY")
                else:
                    # Credit filled = positive statement = sender is counterpart
                    correct_partner_inn = sender_inn
                    correct_partner_name = sender_name
                    _logger.info("CREDIT FILLED in BOG (positive statement) - COUNTERPART is SENDER")

                _logger.info("Looking for partner - VAT: %s, Name: %s", correct_partner_inn, correct_partner_name)

                # Find the correct partner - ONLY by VAT
                correct_partner = self.env['res.partner']
                if correct_partner_inn:
                    correct_partner = self.env['res.partner'].search([('vat', '=', correct_partner_inn)], limit=1)
                    _logger.info("Search by VAT '%s': %s", correct_partner_inn,
                               correct_partner.name if correct_partner else 'NOT FOUND')

                # If not found by VAT, create new partner
                if not correct_partner and correct_partner_inn and correct_partner_name:
                    correct_partner = self.env['res.partner'].create({
                        'name': correct_partner_name,
                        'vat': correct_partner_inn,
                        'company_type': 'company',
                    })
                    _logger.info("CREATED NEW PARTNER: %s (VAT: %s)", correct_partner.name, correct_partner_inn)

                _logger.info("FINAL SELECTED PARTNER: %s (ID: %s, VAT: %s)",
                           correct_partner.name if correct_partner else 'None',
                           correct_partner.id if correct_partner else 'None',
                           correct_partner.vat if correct_partner else 'None')

                # Get standard vals from parent first to ensure all required fields
                standard_vals = super()._apply_lines_for_bank_widget(residual_amount_currency, correct_partner, st_line)

                analytic = _analytic_distribution_from_label(self.env, st_line.payment_ref)

                # If parent returns empty list, create base vals
                if not standard_vals:
                    currency = st_line.foreign_currency_id or st_line.journal_id.currency_id or st_line.company_currency_id
                    vals = {
                        'account_id': mapping.account_id.id,
                        'partner_id': correct_partner.id if correct_partner and mapping.partner_required == 'yes' else False,
                        'name': tbc_transaction.entry_comment or tbc_transaction.entry_document_number or '/',
                        'amount_currency': -residual_amount_currency,
                        'currency_id': currency.id,
                        'analytic_distribution': analytic or False,
                    }
                    standard_vals = [vals]
                    _logger.info("Created new vals with partner_id: %s", vals['partner_id'])
                else:
                    # Update the account from TBC mapping
                    for vals in standard_vals:
                        old_partner_id = vals.get('partner_id')
                        vals['account_id'] = mapping.account_id.id
                        if mapping.partner_required == 'yes' and correct_partner:
                            vals['partner_id'] = correct_partner.id
                        vals['name'] = tbc_transaction.entry_comment or tbc_transaction.entry_document_number or vals.get('name', '/')
                        if analytic:
                            vals['analytic_distribution'] = analytic
                        _logger.info("Updated vals - old partner_id: %s, new partner_id: %s",
                                   old_partner_id, vals.get('partner_id'))

                _logger.info("Returning standard_vals: %s", standard_vals)
                _logger.info("="*80)
                return standard_vals

        # NEW: Check if this is a TBC movement
        tbc_movement_id = st_line.transaction_details.get('tbc_movement_id') if st_line.transaction_details else False

        if self.use_tbc_mapping and tbc_movement_id:
            tbc_movement = self.env['tbc.movements'].browse(tbc_movement_id)

            # Check if record actually exists
            if not tbc_movement.exists():
                _logger.warning("TBC movement %s does not exist, falling back to standard behavior", tbc_movement_id)
                return super()._apply_lines_for_bank_widget(residual_amount_currency, partner, st_line)

            # Use the suggested_mapping which already handles keyword matching
            mapping = tbc_movement.suggested_mapping_id

            if mapping:
                # Get the correct partner from transaction details
                partner_tax_code = st_line.transaction_details.get('partner_tax_code')
                partner_name = st_line.transaction_details.get('partner_name')

                _logger.info("TBC Movement - Looking for partner VAT: %s, Name: %s", partner_tax_code, partner_name)

                # Find the correct partner - ONLY by VAT
                correct_partner = self.env['res.partner']
                if partner_tax_code:
                    correct_partner = self.env['res.partner'].search([('vat', '=', partner_tax_code)], limit=1)
                    _logger.info("TBC Movement - Search by VAT '%s': %s", partner_tax_code,
                               correct_partner.name if correct_partner else 'NOT FOUND')

                # If not found by VAT, create new partner
                if not correct_partner and partner_tax_code and partner_name:
                    correct_partner = self.env['res.partner'].create({
                        'name': partner_name,
                        'vat': partner_tax_code,
                        'company_type': 'company',
                    })
                    _logger.info("TBC Movement - CREATED NEW PARTNER: %s (VAT: %s)", correct_partner.name, partner_tax_code)

                # Get standard vals from parent first to ensure all required fields
                standard_vals = super()._apply_lines_for_bank_widget(residual_amount_currency, correct_partner, st_line)

                analytic = _analytic_distribution_from_label(self.env, st_line.payment_ref)

                # If parent returns empty list, create base vals
                if not standard_vals:
                    currency = st_line.foreign_currency_id or st_line.journal_id.currency_id or st_line.company_currency_id
                    vals = {
                        'account_id': mapping.account_id.id,
                        'partner_id': correct_partner.id if correct_partner and mapping.partner_required == 'yes' else False,
                        'name': tbc_movement.description or tbc_movement.document_number or '/',
                        'amount_currency': -residual_amount_currency,
                        'currency_id': currency.id,
                        'analytic_distribution': analytic or False,
                    }
                    standard_vals = [vals]
                else:
                    # Update the account from TBC mapping
                    for vals in standard_vals:
                        vals['account_id'] = mapping.account_id.id
                        if mapping.partner_required == 'yes' and correct_partner:
                            vals['partner_id'] = correct_partner.id
                        vals['name'] = tbc_movement.description or tbc_movement.document_number or vals.get('name', '/')
                        if analytic:
                            vals['analytic_distribution'] = analytic

                _logger.info("Using TBC mapping: operation_code=%s, account=%s, partner=%s",
                           tbc_movement.operation_code, mapping.account_id.code,
                           correct_partner.name if correct_partner else 'None')
                return standard_vals

        # Fallback to standard behavior
        return super()._apply_lines_for_bank_widget(residual_amount_currency, partner, st_line)


# ============================================================================
# EXTEND BANK STATEMENT LINE
# ============================================================================

class AccountBankStatementLine(models.Model):
    """Extend bank statement line to track TBC transactions and movements"""
    _inherit = 'account.bank.statement.line'

    tbc_transaction_id = fields.Many2one(
        'tbc_payment_integration.tbc_payment_integration',
        string='TBC Transaction',
        help='TBC transaction that generated this statement line',
        compute='_compute_tbc_transaction_id',
        store=True
    )

    # NEW: TBC Movement tracking
    tbc_movement_id = fields.Many2one(
        'tbc.movements',
        string='TBC Movement',
        help='TBC movement that generated this statement line',
        compute='_compute_tbc_movement_id',
        store=True
    )

    @api.depends('transaction_details')
    def _compute_tbc_transaction_id(self):
        """Extract TBC transaction ID from transaction_details JSON"""
        for line in self:
            if line.transaction_details and isinstance(line.transaction_details, dict):
                tbc_id = line.transaction_details.get('tbc_transaction_id')
                if tbc_id:
                    line.tbc_transaction_id = tbc_id
                else:
                    line.tbc_transaction_id = False
            else:
                line.tbc_transaction_id = False

    @api.depends('transaction_details')
    def _compute_tbc_movement_id(self):
        """Extract TBC movement ID from transaction_details JSON"""
        for line in self:
            if line.transaction_details and isinstance(line.transaction_details, dict):
                movement_id = line.transaction_details.get('tbc_movement_id')
                if movement_id:
                    line.tbc_movement_id = movement_id
                else:
                    line.tbc_movement_id = False
            else:
                line.tbc_movement_id = False


# ============================================================================
# TBC MOVEMENTS MODEL - Keep for compatibility
# ============================================================================

class TBCMovements(models.Model):
    """TBC Movements - Reworked for standard Odoo reconciliation (same as BOG)"""
    _name = 'tbc.movements'
    _description = 'TBC Movements'
    _order = 'value_date desc, id desc'

    # TBC Movement Data Fields
    movement_id = fields.Char(string='Movement ID', index=True)
    external_payment_id = fields.Char(string='External Payment ID')
    debit_credit = fields.Char(string='Debit/Credit')  # '0' = debit (outgoing), '1' = credit (incoming)
    value_date = fields.Date(string='Value Date', index=True)
    description = fields.Text(string='Description')
    amount = fields.Float(string='Amount')
    currency = fields.Char(string='Currency')
    account_number = fields.Char(string='Account Number')
    account_name = fields.Char(string='Account Name')
    additional_information = fields.Text(string='Additional Information')
    document_date = fields.Date(string='Document Date')
    document_number = fields.Char(string='Document Number')
    partner_account_number = fields.Char(string='Partner Account Number')
    partner_name = fields.Char(string='Partner Name')
    partner_tax_code = fields.Char(string='Partner Tax Code', index=True)
    taxpayer_code = fields.Char(string='Taxpayer Code')
    taxpayer_name = fields.Char(string='Taxpayer Name')
    operation_code = fields.Char(string='Operation Code', index=True)
    partner_personal_number = fields.Char(string='Partner Personal Number')
    partner_document_type = fields.Char(string='Partner Document Type')
    partner_document_number = fields.Char(string='Partner Document Number')
    parent_external_payment_id = fields.Char(string='Parent External Payment ID')
    status_code = fields.Char(string='Status Code')
    transaction_type = fields.Char(string='Transaction Type')
    get_account_movements_response_io_id = fields.Char(string='Response IO ID')

    # NEW: Store fetched bank account
    my_bank_id = fields.Char(string='Fetched Bank Account')

    # NEW: Computed mapping based on operation_code
    operation_code_mapping = fields.Many2one(
        'tbc.code.mapping',
        string='Operation Code Mapping',
        compute='_compute_operation_code_mapping',
        store=True
    )

    # NEW: Auto-detected partner (same logic as BOG)
    partner_id = fields.Many2one(
        'res.partner',
        string='Detected Partner',
        compute='_compute_partner_id',
        store=True,
        help='Partner auto-detected from tax code or name'
    )

    # NEW: Suggested mapping (same logic as BOG but with operation_code)
    suggested_mapping_id = fields.Many2one(
        'tbc.code.mapping',
        string='Suggested Mapping',
        compute='_compute_suggested_mapping',
        store=True
    )

    # NEW: State management for Odoo-standard flow (same as BOG)
    state = fields.Selection([
        ('draft', 'Draft - Not Imported'),
        ('imported', 'Imported - Statement Line Created'),
        ('reconciled', 'Reconciled'),
        ('error', 'Error')
    ], string='Status', default='draft', tracking=True)

    # NEW: Link to created bank statement line (same as BOG)
    statement_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Statement Line',
        help='The bank statement line created from this movement',
        readonly=True
    )

    # NEW: Computed fields for reconciliation info (same as BOG)
    is_reconciled = fields.Boolean(
        string='Is Reconciled',
        related='statement_line_id.is_reconciled',
        store=True
    )

    # Legacy fields (keep for compatibility)
    payment_id = fields.Many2one(
        'account.payment',
        string='Related Payment (Deprecated)',
        help='Legacy field - not used in new flow'
    )
    related_journal_entry_id = fields.Many2one(
        'account.move',
        string='Related Journal Entry (Deprecated)',
        help='Legacy field - not used in new flow'
    )

    @api.depends('operation_code')
    def _compute_operation_code_mapping(self):
        """Compute the mapping based on operation code"""
        for record in self:
            if record.operation_code:
                mapping = self.env['tbc.code.mapping'].search([
                    ('code_field', '=', record.operation_code)
                ], limit=1)
                record.operation_code_mapping = mapping
            else:
                record.operation_code_mapping = False

    @api.depends('partner_tax_code', 'partner_name', 'debit_credit')
    def _compute_partner_id(self):
        """Auto-detect partner from partner_tax_code or partner_name (same logic as BOG)"""
        for record in self:
            partner = False

            # For TBC movements, partner_tax_code and partner_name are always the counterpart
            partner_vat = record.partner_tax_code
            partner_name = record.partner_name

            # Step 1: Try to find by VAT (partner_tax_code) - highest priority
            if partner_vat:
                partner = self.env['res.partner'].search([
                    ('vat', '=', partner_vat)
                ], limit=1)

            # Step 2: If not found by VAT, try by exact name
            if not partner and partner_name:
                partner = self.env['res.partner'].search([
                    ('name', '=', partner_name)
                ], limit=1)

            # Step 3: If still not found, try fuzzy name match
            if not partner and partner_name:
                partner = self.env['res.partner'].search([
                    ('name', '=ilike', partner_name)
                ], limit=1)

            record.partner_id = partner

    @api.depends('operation_code', 'description', 'additional_information', 'debit_credit')
    def _compute_suggested_mapping(self):
        """Compute suggested mapping based on TBC Movements logic"""
        for record in self:
            mapping = False
            if record.operation_code:
                # Use debit_credit field directly: '0' = debit mapping, '1' = credit mapping
                transaction_type = 'debit' if record.debit_credit == '0' else 'credit'

                # Search for mappings
                all_mappings = self.env['tbc.code.mapping'].search([
                    ('code_field', '=', record.operation_code)
                ])

                type_filtered = all_mappings.filtered(
                    lambda m: m.debit_credit == transaction_type
                )

                if type_filtered:
                    # Try to match by comment keywords in description or additional_information
                    comment_text = (record.description or '') + ' ' + (record.additional_information or '')
                    comment_text = comment_text.lower()

                    for map_rec in type_filtered:
                        if map_rec.comment and map_rec.comment.strip():
                            keywords = [kw.strip().lower() for kw in map_rec.comment.split(',')]
                            if any(kw in comment_text for kw in keywords):
                                mapping = map_rec
                                break

                    # Fallback to empty comment mapping or first
                    if not mapping:
                        empty_comment = type_filtered.filtered(lambda m: not m.comment or not m.comment.strip())
                        mapping = empty_comment[0] if empty_comment else type_filtered[0]
                elif all_mappings:
                    mapping = all_mappings[0]

            record.suggested_mapping_id = mapping

    def _get_currency_rate(self, currency_name, transaction_date):
        """
        Get currency rate for converting to GEL from res.currency.rate (for TBC Movements)
        Currency rate is stored in company_rate field, date in name field (Date type)
        Raises UserError if no rate is found for the transaction date
        """
        if not currency_name or currency_name == 'GEL':
            return 1.0

        if not transaction_date:
            raise UserError(
                f"No transaction date provided for currency conversion from {currency_name} to GEL.\n"
                f"Please ensure all movements have valid dates."
            )

        # Find the currency
        currency = self.env['res.currency'].search([('name', '=', currency_name)], limit=1)
        if not currency:
            raise UserError(
                f"Currency '{currency_name}' not found in the system.\n"
                f"Please add this currency to res.currency before importing movements."
            )

        # Parse date string to date object
        if isinstance(transaction_date, str):
            # Try multiple date formats
            date_obj = None
            for date_format in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%d/%m/%Y']:
                try:
                    date_obj = datetime.strptime(transaction_date, date_format)
                    break
                except ValueError:
                    continue

            if not date_obj:
                raise UserError(
                    f"Invalid movement date format: {transaction_date}\n"
                    f"Expected formats: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS or DD/MM/YYYY"
                )
        else:
            date_obj = transaction_date

        formatted_date_display = date_obj.strftime('%d/%m/%Y')  # For display

        # Search for the rate with matching currency and date in name field
        # Note: name field in res.currency.rate is a Date field, so we search with date object
        search_date = date_obj.date() if hasattr(date_obj, 'date') else date_obj
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id', '=', currency.id),
            ('name', '=', search_date)
        ], limit=1)

        if rate_record and rate_record.company_rate:
            _logger.info(f"Found rate for {currency_name} on {formatted_date_display}: {rate_record.company_rate}")
            return float(rate_record.company_rate)
        else:
            # No exact match found - raise error
            raise UserError(
                f"Currency exchange rate not found!\n\n"
                f"Currency: {currency_name}\n"
                f"Date: {formatted_date_display}\n\n"
                f"Please update currency exchange rates in res.currency.rate for the selected dates.\n"
                f"Required format:\n"
                f"  - Currency: {currency_name}\n"
                f"  - Name (date): {formatted_date_display}\n"
                f"  - Company Rate: (e.g., 0.319560285048)"
            )

    def _convert_to_gel(self, amount, currency_name, transaction_date):
        """Convert amount from foreign currency to GEL using res.currency.rate"""
        if not amount or currency_name == 'GEL':
            return amount

        rate = self._get_currency_rate(currency_name, transaction_date)
        converted_amount = amount / rate if rate else amount
        _logger.info(f"Converting {amount} {currency_name} to GEL: {converted_amount} (rate: {rate})")
        return converted_amount

    def action_create_statement_lines(self):
        """
        NEW METHOD: Create bank statement lines from TBC movements (same as BOG)
        This is the main entry point for the new Odoo-standard flow
        """
        created_count = 0
        skipped_count = 0

        for movement in self:
            if movement.state == 'imported' and movement.statement_line_id:
                _logger.info("Movement %s already has statement line %s, skipping",
                           movement.id, movement.statement_line_id.id)
                skipped_count += 1
                continue

            try:
                statement_line = movement._create_bank_statement_line()
                movement.write({
                    'statement_line_id': statement_line.id,
                    'state': 'imported'
                })
                _logger.info("Created statement line %s for movement %s", statement_line.id, movement.id)
                created_count += 1
            except Exception as e:
                movement.state = 'error'
                _logger.error("Failed to create statement line for movement %s: %s", movement.id, str(e))
                skipped_count += 1
                raise UserError(_('Failed to create statement line: %s') % str(e))

        message = _('%d bank statement lines created successfully') % created_count
        if skipped_count > 0:
            message += _(', %d already imported') % skipped_count

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_bank_statement_line(self, journal=None):
        """
        Create a bank statement line from this TBC movement (same logic as BOG)
        Args:
            journal: Optional journal to use. If not provided, will auto-detect.
        Returns: account.bank.statement.line record
        """
        self.ensure_one()

        # Check if statement line already exists for this movement
        if self.statement_line_id:
            _logger.info("Statement line already exists for movement %s", self.id)
            return self.statement_line_id

        # Determine amount and direction
        is_debit = self.debit_credit == '0'  # '0' = debit (outgoing), '1' = credit (incoming)
        amount = abs(self.amount)

        # Convert amount to GEL if needed
        movement_currency = self.currency or 'GEL'
        if movement_currency != 'GEL' and amount > 0:
            _logger.info(f"Converting statement line amount from {movement_currency} to GEL for movement {self.id}")
            amount = self._convert_to_gel(amount, movement_currency, self.value_date)

        # Amount should be positive for inbound, negative for outbound
        signed_amount = -amount if is_debit else amount

        # Find appropriate bank journal (use provided or auto-detect)
        if not journal:
            journal = self._find_bank_journal()
        if not journal:
            raise UserError(_('No bank journal found for account: %s') % self.account_number)

        # Check if a statement line already exists with same movement_id and journal
        if self.movement_id:
            existing_line = self.env['account.bank.statement.line'].search([
                ('journal_id', '=', journal.id),
                ('transaction_details', '!=', False)
            ])
            for line in existing_line:
                if line.transaction_details and isinstance(line.transaction_details, dict):
                    if line.transaction_details.get('movement_id') == self.movement_id:
                        _logger.warning("Statement line already exists for movement_id %s, linking to movement %s",
                                      self.movement_id, self.id)
                        self.write({
                            'statement_line_id': line.id,
                            'state': 'imported'
                        })
                        return line

        # Prepare payment reference
        payment_ref = self.description or self.document_number or '/'

        # For TBC movements, partner is always the counterpart
        # Find partner by partner_tax_code or partner_name
        partner = False
        if self.partner_tax_code:
            partner = self.env['res.partner'].search([('vat', '=', self.partner_tax_code)], limit=1)
        if not partner and self.partner_name:
            partner = self.env['res.partner'].search([('name', '=', self.partner_name)], limit=1)
        if not partner and self.partner_name:
            partner = self.env['res.partner'].search([('name', '=ilike', self.partner_name)], limit=1)

        # Prepare bank statement line values
        # Note: All amounts are now in GEL (converted in wizard), so no foreign_currency_id needed
        vals = {
            'journal_id': journal.id,
            'date': self.value_date or fields.Date.today(),
            'payment_ref': payment_ref,
            'partner_id': partner.id if partner else False,
            'amount': signed_amount,
            'transaction_type': self.operation_code,  # Use operation_code as transaction type
        }

        # Note: We don't set foreign_currency_id anymore because:
        # 1. All journals use GEL as currency_id
        # 2. Amounts have been converted to GEL in the wizard
        # 3. Currency is only identified by journal name suffix

        # Store TBC movement details in transaction_details JSON field
        vals['transaction_details'] = {
            'tbc_movement_id': self.id,
            'movement_id': self.movement_id,
            'operation_code': self.operation_code,
            'description': self.description,  # NEW: For keyword matching
            'additional_information': self.additional_information,  # NEW: Additional comment
            'partner_tax_code': self.partner_tax_code,
            'partner_name': self.partner_name,
            'partner_account_number': self.partner_account_number,
        }

        # Create statement line
        statement_line = self.env['account.bank.statement.line'].create(vals)

        return statement_line

    def _find_bank_journal(self):
        """
        Find the appropriate bank journal for this movement
        Journal is identified by currency suffix in name (e.g., GE29BG0000000586405640USD)
        """
        self.ensure_one()

        # Try to find journal by account number and currency
        account_number = self.account_number or self.my_bank_id
        movement_currency = self.currency or 'GEL'

        if account_number:
            # Clean account number (remove all currency suffixes)
            clean_account = account_number.replace(' ', '')
            for curr in ['GEL', 'USD', 'EUR', 'RUB', 'GBP']:
                clean_account = clean_account.replace(curr, '')

            # Build journal name with currency suffix
            journal_name_with_currency = f"{clean_account}{movement_currency}"

            # Get currency record for filtering
            currency_record = self.env['res.currency'].search([('name', '=', movement_currency)], limit=1)

            # Search for journal with matching name (account + currency suffix) and currency_id
            domain = [
                ('type', '=', 'bank'),
                ('name', '=', journal_name_with_currency)
            ]
            if currency_record:
                domain.append(('currency_id', '=', currency_record.id))

            journal = self.env['account.journal'].search(domain, limit=1)

            if journal:
                _logger.debug(f"Found journal by name with currency: {journal.name}")
                return journal

            # Fallback: Try exact match with original account number and currency filter
            domain = [
                ('type', '=', 'bank'),
                ('name', '=', account_number)
            ]
            if currency_record:
                domain.append(('currency_id', '=', currency_record.id))

            journal = self.env['account.journal'].search(domain, limit=1)

            if journal:
                return journal

            # Try to find by bank_account_id with currency filter
            bank_account = self.env['res.partner.bank'].search([
                '|',
                ('acc_number', '=', account_number),
                ('acc_number', '=', clean_account)
            ], limit=1)

            if bank_account and bank_account.journal_id:
                # Verify currency matches
                if currency_record and bank_account.journal_id.currency_id == currency_record:
                    return bank_account.journal_id
                elif not currency_record:
                    return bank_account.journal_id

        # Fallback to any bank journal with matching currency
        if currency_record:
            return self.env['account.journal'].search([
                ('type', '=', 'bank'),
                ('currency_id', '=', currency_record.id)
            ], limit=1)

        return self.env['account.journal'].search([('type', '=', 'bank')], limit=1)

    def _create_bank_statement_line_with_journal(self, journal):
        """Wrapper method to create statement line with specific journal and update state"""
        statement_line = self._create_bank_statement_line(journal)
        self.write({
            'statement_line_id': statement_line.id,
            'state': 'imported'
        })
        return statement_line

    def action_view_statement_line(self):
        """Open the related bank statement line (same as BOG)"""
        self.ensure_one()
        if not self.statement_line_id:
            raise UserError(_('No statement line created yet'))

        return {
            'name': _('Bank Statement Line'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'res_id': self.statement_line_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_reconciliation(self):
        """Open reconciliation widget for this movement's statement line (same as BOG)"""
        self.ensure_one()
        if not self.statement_line_id:
            raise UserError(_('Please create statement line first'))

        # Return action to open bank reconciliation widget
        return {
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': {
                'statement_line_ids': [self.statement_line_id.id],
                'company_ids': self.statement_line_id.company_id.ids,
            }
        }


# ============================================================================
# PARTNER SELECTION WIZARD - Keep for compatibility
# ============================================================================

class TBCPartnerSelectionWizard(models.TransientModel):
    """Partner Selection Wizard - Keep for manual partner assignment"""
    _name = 'tbc.partner.selection.wizard'
    _description = 'TBC Partner Selection Wizard'

    transaction_id = fields.Many2one(
        'tbc_payment_integration.tbc_payment_integration',
        string='Transaction',
        required=True
    )
    partner_id = fields.Many2one('res.partner', string='Select Partner', required=False)
    partner_name = fields.Char(string='Partner Name from Transaction', readonly=True)
    partner_inn = fields.Char(string='Partner INN from Transaction', readonly=True)
    transaction_type = fields.Char(string='Transaction Type', readonly=True)

    def action_confirm_partner(self):
        """Confirm partner and update transaction"""
        if not self.partner_id:
            raise UserError(_('Please select a partner to continue.'))

        self.transaction_id.partner_id = self.partner_id
        return {'type': 'ir.actions.act_window_close'}


# ============================================================================
# ACCOUNT PAYMENT EXTENSION - Keep for compatibility
# ============================================================================

class AccountPayment(models.Model):
    """Keep payment extension for backward compatibility"""
    _inherit = 'account.payment'

    tbc_transaction_id = fields.Many2one(
        'tbc_payment_integration.tbc_payment_integration',
        string='TBC Transaction (Deprecated)',
        help='Legacy field - not used in new reconciliation flow'
    )
    tbc_movement_id = fields.Many2one(
        'tbc.movements',
        string='TBC Movement (Deprecated)',
        help='Legacy field - not used in new reconciliation flow'
    )



