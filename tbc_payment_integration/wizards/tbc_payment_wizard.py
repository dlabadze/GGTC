import requests
import base64
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
import pandas as pd
from datetime import datetime

# Configure logging
_logger = logging.getLogger(__name__)



from odoo import models, fields, api

from odoo import models, fields, api

class BogPaymentWizard(models.TransientModel):
    _name = 'bog.payment.wizard'
    _description = 'BOG Payment Integration Wizard'

    api_key = fields.Char('API Key')
    client_secret = fields.Char('Client Secret')
    acc_number = fields.Char('Account Number')
    currency = fields.Selection([
        ('GEL', 'GEL'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('RUB', 'RUB'),
        ('GBP', 'GBP'),
    ], string='Currency', default='GEL', required=True)
    start_date = fields.Date('პერიოდის დასაწყისი', default=fields.Date.today)
    end_date = fields.Date('პერიოდის დასასრული', default=fields.Date.today)

    company_id = fields.Many2one('res.company', string='Company')
    selected_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='აირჩიეთ ბანკის ანგარიში',
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            # Fetch bank accounts related to the selected company
            bank_accounts = self.env['res.partner.bank'].search([('company_id', '=', self.company_id.id)])
            return {
                'domain': {'selected_bank_account_id': [('id', 'in', bank_accounts.ids)]}
            }
        else:
            return {
                'domain': {'selected_bank_account_id': []}
            }

    def _check_existing_records(self, records_data):
        """
        Bulk check for existing records to improve performance.
        Returns a set of existing DocumentKeys.
        """
        document_keys = [record.get("document_key") for record in records_data if record.get("document_key")]

        if not document_keys:
            return set()

        existing_records = self.env['tbc_payment_integration.tbc_payment_integration'].search([
            ('document_key', 'in', document_keys)
        ])

        return set(existing_records.mapped('document_key'))

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
        """
        Convert amount from foreign currency to GEL using res.currency.rate
        """
        if not amount or currency_name == 'GEL':
            return amount

        rate = self._get_currency_rate(currency_name, transaction_date)
        converted_amount = amount / rate if rate else amount
        _logger.info(f"Converting {amount} {currency_name} to GEL: {converted_amount} (rate: {rate})")
        return converted_amount

    def _find_or_create_partner(self, record_data):
        """
        Find or create partner from transaction beneficiary/sender details.
        Priority: 1. Search by VAT (INN), 2. Search by name (exact), 3. Search by name (fuzzy), 4. Create new only if VAT exists
        """
        # Determine if this is debit or credit to choose sender/beneficiary
        is_debit = record_data.get('entry_amount_debit', 0) > 0

        # For debit transactions, partner is beneficiary (we paid them)
        # For credit transactions, partner is sender (they paid us)
        if is_debit:
            partner_name = record_data.get('beneficiary_details_name')
            partner_inn = record_data.get('beneficiary_details_inn')
        else:
            partner_name = record_data.get('sender_details_name')
            partner_inn = record_data.get('sender_details_inn')

        if not partner_name and not partner_inn:
            _logger.debug("No partner information found in transaction")
            return False

        # Step 1: Try to find by VAT (INN) - highest priority
        if partner_inn:
            partner = self.env['res.partner'].search([('vat', '=', partner_inn)], limit=1)
            if partner:
                _logger.debug(f"Found existing partner by VAT: {partner.name} (VAT: {partner_inn})")
                return partner

        # Step 2: Try to find by exact name match
        if partner_name:
            partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
            if partner:
                _logger.debug(f"Found existing partner by exact name: {partner.name}")
                # Update VAT if partner found but VAT was missing
                if partner_inn and not partner.vat:
                    partner.write({'vat': partner_inn})
                    _logger.info(f"Updated partner {partner.name} with VAT: {partner_inn}")
                return partner

        # Step 3: Try to find by fuzzy name match (case insensitive)
        if partner_name:
            partner = self.env['res.partner'].search([('name', '=ilike', partner_name)], limit=1)
            if partner:
                _logger.debug(f"Found existing partner by fuzzy name: {partner.name}")
                # Update VAT if partner found but VAT was missing
                if partner_inn and not partner.vat:
                    partner.write({'vat': partner_inn})
                    _logger.info(f"Updated partner {partner.name} with VAT: {partner_inn}")
                return partner

        # Step 4: Only create new partner if we have VAT or if name is significant
        if partner_name and partner_inn:
            # Create partner only if we have VAT
            partner_vals = {
                'name': partner_name,
                'vat': partner_inn,
                'company_type': 'company',
            }
            partner = self.env['res.partner'].create(partner_vals)
            _logger.info(f"Created new partner: {partner.name} (VAT: {partner_inn})")
            return partner
        elif partner_name and not partner_inn:
            # Don't create partner without VAT - just log and return False
            _logger.info(f"Partner not found for name '{partner_name}' without VAT - skipping creation to avoid duplicates")
            return False

        return False

    def _find_or_create_journal(self, account_number, currency='GEL'):
        """
        Find or create bank journal matching the account number and currency.
        Account number format: GE29BG0000000586405640
        Creates separate journals for each currency with format: GE29BG0000000586405640GEL
        Sets currency_id to the appropriate currency for proper filtering
        """
        if not account_number:
            _logger.warning("No account number provided")
            return False

        # Clean account number (remove spaces and any existing currency suffix)
        clean_acc_number = account_number.replace(' ', '')
        for curr in ['GEL', 'USD', 'EUR', 'RUB', 'GBP']:
            clean_acc_number = clean_acc_number.replace(curr, '')

        # Build full account identifier with currency
        full_account_with_currency = f"{clean_acc_number}{currency}"

        # Get currency record
        currency_record = self.env['res.currency'].search([('name', '=', currency)], limit=1)
        if not currency_record:
            _logger.error(f"Currency '{currency}' not found in the system")
            return False

        # Step 1: Try to find existing journal by full account number with currency and currency_id
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('name', '=', full_account_with_currency),
            ('currency_id', '=', currency_record.id)
        ], limit=1)

        if journal:
            _logger.debug(f"Found existing journal for account {full_account_with_currency}: {journal.name}")
            return journal

        # Step 2: Search in res.partner.bank for matching account (without currency suffix)
        bank_account = self.env['res.partner.bank'].search([
            ('acc_number', '=', clean_acc_number)
        ], limit=1)

        # Step 3: Create new bank journal with currency in name and currency_id
        journal_name = full_account_with_currency  # Full account number with currency
        journal_code = f"BNK{clean_acc_number[-6:]}{currency[:2]}"  # Use last 6 digits + currency code

        # Ensure unique code
        existing_code = self.env['account.journal'].search([('code', '=', journal_code)], limit=1)
        if existing_code:
            journal_code = f"BNK{clean_acc_number[-8:]}{currency[:2]}"  # Try with 8 chars

        journal_vals = {
            'name': journal_name,
            'code': journal_code,
            'type': 'bank',
            'bank_account_id': bank_account.id if bank_account else False,
            'currency_id': currency_record.id,
        }

        try:
            journal = self.env['account.journal'].create(journal_vals)
            _logger.info(f"Created new bank journal: {journal.name} (Code: {journal.code}, Currency: {currency})")
            return journal
        except Exception as e:
            _logger.error(f"Failed to create journal for account {clean_acc_number} with currency {currency}: {e}")
            return False

    def fetch_transactions(self):
        _logger.info("Starting transaction fetch process")

        api_key = self.env.user.bog_client_secret
        client_secret = self.env.user.bog_client_id
        currency = self.currency
        start_date = self.start_date
        end_date = self.end_date

        _logger.info(f"Api Key: {api_key}")
        _logger.info(f"Client Secret: {client_secret}")

        # Fetch the account number from the selected bank
        if not self.selected_bank_account_id:
            _logger.error("No bank selected.")
            return

        acc_number = self.selected_bank_account_id.acc_number.replace(' ', '')

        if not acc_number:
            _logger.error("No account number found for the selected bank.")
            return

        _logger.info(f"Fetching transactions for bank: {acc_number}")

        # Authentication
        auth_string = f"{api_key}:{client_secret}"
        auth_header = base64.b64encode(auth_string.encode()).decode()

        data = {
            'grant_type': 'client_credentials'
        }

        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        base_url = 'https://account.bog.ge/auth/realms/bog/protocol/openid-connect/token'

        try:
            response = requests.post(base_url, headers=headers, data=data)
            response.raise_for_status()
            response_data = response.json()
            access_token = response_data.get('access_token')
            _logger.info("Authentication successful, access token obtained")
        except requests.exceptions.RequestException as e:
            _logger.error("Failed to authenticate: %s", e)
            return

        # Step 1: Generate the statement and get the statement ID
        statement_url = f"https://api.businessonline.ge/api/statement/{acc_number}/{currency}/{start_date}/{end_date}"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        try:
            response = requests.get(statement_url, headers=headers, timeout=300)
            response.raise_for_status()
            response_data = response.json()

            # Extract statement ID and total count from the initial response
            statement_id = response_data.get('Id')
            total_count = response_data.get('Count', 0)
            records = response_data.get('Records', [])

            _logger.info(f"Statement generated with ID: {statement_id}, Total records: {total_count}")
            _logger.info(f"Fetched {len(records)} records from first page")

            if not statement_id:
                _logger.error("No statement ID received from the API")
                return

        except requests.exceptions.RequestException as e:
            _logger.error("Failed to generate statement: %s", e)
            return

        # Step 2: Fetch all pages if there are more than 1000 records
        all_records = records.copy()  # Start with records from the first page

        if total_count > 1000:
            # Calculate total number of pages (1000 records per page)
            total_pages = (total_count + 999) // 1000  # Ceiling division
            _logger.info(f"Total pages to fetch: {total_pages}")

            # Fetch remaining pages (starting from page 2 since we already have page 1)
            for page_num in range(2, total_pages + 1):
                page_url = f"https://api.businessonline.ge/api/statement/{acc_number}/{currency}/{statement_id}/{page_num}"

                try:
                    page_response = requests.get(page_url, headers=headers, timeout=300)
                    page_response.raise_for_status()
                    page_records = page_response.json()

                    # The page response is directly an array of records
                    if isinstance(page_records, list):
                        all_records.extend(page_records)
                        _logger.info(f"Fetched {len(page_records)} records from page {page_num}")
                    else:
                        _logger.warning(f"Unexpected response format for page {page_num}: {type(page_records)}")

                except requests.exceptions.RequestException as e:
                    _logger.error(f"Failed to fetch page {page_num}: %s", e)
                    # Continue with other pages even if one fails
                    continue

        _logger.info(f"Total records fetched across all pages: {len(all_records)}")

        # Log raw records coming from bank - ALL RECORDS WITH AMOUNTS
        if all_records:
            _logger.info("=" * 80)
            _logger.info(f"RAW RECORDS FROM BOG BANK - ALL {len(all_records)} RECORDS")
            _logger.info("=" * 80)

            # Log amounts for ALL records to verify completeness
            for i, record in enumerate(all_records, start=1):
                entry_amount_debit = record.get("EntryAmountDebit", 0)
                entry_amount_credit = record.get("EntryAmountCredit", 0)
                entry_amount_debit_base = record.get("EntryAmountDebitBase", 0)
                entry_amount_credit_base = record.get("EntryAmountCreditBase", 0)
                entry_date = record.get("EntryDate", "N/A")
                document_key = record.get("DocumentKey", "N/A")

                _logger.info(
                    f"Record {i}/{len(all_records)}: "
                    f"Date={entry_date}, "
                    f"DocKey={document_key}, "
                    f"Debit={entry_amount_debit}, "
                    f"Credit={entry_amount_credit}, "
                    f"DebitBase={entry_amount_debit_base}, "
                    f"CreditBase={entry_amount_credit_base}"
                )

            _logger.info("=" * 80)
            _logger.info(f"VERIFICATION: Logged amounts for all {len(all_records)} records across all pages")
            _logger.info("=" * 80)

        # Helper function to normalize entry id for comparison
        def normalize_entry_id(entry_id):
            """Convert entry id to string and handle different formats"""
            if entry_id is None or entry_id is False:
                return None

            # Convert to string first
            entry_id_str = str(entry_id)

            # Remove .0 suffix if present (handles float to string conversion)
            if entry_id_str.endswith('.0'):
                entry_id_str = entry_id_str[:-2]

            return entry_id_str

        # Step 3: Process all records and prepare data
        data = []
        incoming_entry_ids = []

        for record in all_records:
            # Normalize the entry id
            raw_entry_id = record.get("EntryId")
            normalized_entry_id = normalize_entry_id(raw_entry_id)

            # Also normalize document key for storage
            raw_doc_key = record.get("DocumentKey")
            normalized_doc_key = normalize_entry_id(raw_doc_key)

            record_data = {
                "entry_date": record.get("EntryDate", False),
                "entry_document_number": record.get("EntryDocumentNumber", False),
                "entry_account_number": record.get("EntryAccountNumber", False),
                "entry_amount_debit": record.get("EntryAmountDebit", False),
                "entry_amount_debit_base": record.get("EntryAmountDebitBase", False),
                "entry_amount_credit": record.get("EntryAmountCredit", False),
                "entry_amount_credit_base": record.get("EntryAmountCreditBase", False),
                "entry_amount_base": record.get("EntryAmountBase", False),
                "entry_amount": record.get("EntryAmount", False),
                "entry_comment": record.get("EntryComment", False),
                "entry_department": record.get("EntryDepartment", False),
                "entry_account_point": record.get("EntryAccountPoint", False),
                "document_product_group": record.get("DocumentProductGroup", False),
                "document_value_date": record.get("DocumentValueDate", False),
                # Sender Details
                "sender_details_name": record.get("SenderDetails", {}).get("Name", False),
                "sender_details_inn": record.get("SenderDetails", {}).get("Inn", False),
                "sender_details_account_number": record.get("SenderDetails", {}).get("AccountNumber", False),
                "sender_details_bank_code": record.get("SenderDetails", {}).get("BankCode", False),
                "sender_details_bank_name": record.get("SenderDetails", {}).get("BankName", False),
                # Beneficiary Details
                "beneficiary_details_name": record.get("BeneficiaryDetails", {}).get("Name", False),
                "beneficiary_details_inn": record.get("BeneficiaryDetails", {}).get("Inn", False),
                "beneficiary_details_account_number": record.get("BeneficiaryDetails", {}).get("AccountNumber", False),
                "beneficiary_details_bank_code": record.get("BeneficiaryDetails", {}).get("BankCode", False),
                "beneficiary_details_bank_name": record.get("BeneficiaryDetails", {}).get("BankName", False),
                # Document Fields
                "document_treasury_code": record.get("DocumentTreasuryCode", False),
                "document_nomination": record.get("DocumentNomination", False),
                "document_information": record.get("DocumentInformation", False),
                "document_source_amount": record.get("DocumentSourceAmount", False),
                "document_source_currency": record.get("DocumentSourceCurrency", False),
                "document_destination_amount": record.get("DocumentDestinationAmount", False),
                "document_destination_currency": record.get("DocumentDestinationCurrency", False),
                "document_receive_date": record.get("DocumentReceiveDate", False),
                "document_branch": record.get("DocumentBranch", False),
                "document_department": record.get("DocumentDepartment", False),
                "document_actual_date": record.get("DocumentActualDate", False),
                "document_expiry_date": record.get("DocumentExpiryDate", False),
                "document_rate_limit": record.get("DocumentRateLimit", False),
                "document_rate": record.get("DocumentRate", False),
                "document_registration_rate": record.get("DocumentRegistrationRate", False),
                "document_sender_institution": record.get("DocumentSenderInstitution", False),
                "document_intermediary_institution": record.get("DocumentIntermediaryInstitution", False),
                "document_beneficiary_institution": record.get("DocumentBeneficiaryInstitution", False),
                "document_payee": record.get("DocumentPayee", False),
                "document_correspondent_account_number": record.get("DocumentCorrespondentAccountNumber", False),
                "document_correspondent_bank_code": record.get("DocumentCorrespondentBankCode", False),
                "document_correspondent_bank_name": record.get("DocumentCorrespondentBankName", False),
                "document_key": normalized_doc_key,  # Use normalized key
                "entry_id": normalized_entry_id,  # Use normalized entry id
                "doc_comment": record.get("DocComment", False),
                "document_payer_inn": record.get("DocumentPayerInn", False),
                "document_payer_name": record.get("DocumentPayerName", False),
                "my_bank_id": acc_number,
            }

            data.append(record_data)

            # Collect entry ids for duplicate checking
            if normalized_entry_id:
                incoming_entry_ids.append(normalized_entry_id)

        if not incoming_entry_ids:
            _logger.warning("No valid entry ids found in incoming data")
            return

        _logger.info(f"Processing {len(incoming_entry_ids)} records with entry ids")

        # Step 4: Check for existing records using multiple comparison methods
        try:
            # Method 1: Direct comparison with normalized entry ids
            existing_records_direct = self.env['tbc_payment_integration.tbc_payment_integration'].search([
                ('entry_id', 'in', incoming_entry_ids)
            ])

            # Method 2: Also check with .0 suffix added (in case database stores them differently)
            ids_with_suffix = [f"{entry_id}.0" for entry_id in incoming_entry_ids]
            existing_records_suffix = self.env['tbc_payment_integration.tbc_payment_integration'].search([
                ('entry_id', 'in', ids_with_suffix)
            ])

            # Combine both result sets
            all_existing_records = existing_records_direct | existing_records_suffix

            # Create a set of existing (entry_id, bank_account) tuples for fast lookup
            # This allows same entry_id on different bank accounts (internal transfers)
            existing_entry_ids_with_account = set()
            for record in all_existing_records:
                normalized_id = normalize_entry_id(record.entry_id)
                if normalized_id:
                    bank_account = record.my_bank_id or ''
                    existing_entry_ids_with_account.add((normalized_id, bank_account))

            _logger.info(f"Found {len(existing_entry_ids_with_account)} existing records in database")

            # Debug: Log some existing ids
            if existing_entry_ids_with_account:
                sample_ids = list(existing_entry_ids_with_account)[:5]
                _logger.info(f"Sample existing entry ids with account: {sample_ids}")

            created_count = 0
            skipped_count = 0

            # Step 5: Process each record
            for record in data:
                entry_id = record.get("entry_id")

                # Skip records without EntryId
                if not entry_id:
                    _logger.warning("Skipping record without EntryId: %s", record.get("document_key", "Unknown"))
                    skipped_count += 1
                    continue

                # Check if record with this EntryId AND same bank account already exists
                record_bank_account = record.get("my_bank_id", '')
                record_signature = (entry_id, record_bank_account)

                if record_signature in existing_entry_ids_with_account:
                    _logger.info(f"Record with EntryId {entry_id} on account {record_bank_account} already exists, skipping")
                    skipped_count += 1
                    continue

                # Create new record if it doesn't exist
                try:
                    # Step 1: Find or create partner from transaction details
                    partner = self._find_or_create_partner(record)
                    if partner:
                        record['partner_id'] = partner.id

                    # Step 2: Create transaction record (amounts stay in original currency)
                    new_record = self.env['tbc_payment_integration.tbc_payment_integration'].create(record)
                    created_count += 1

                    # Step 3: Find or create journal for this account number with currency
                    journal = self._find_or_create_journal(record.get('my_bank_id'), currency)

                    # Step 4: Auto-create statement line (conversion happens here)
                    if journal and not new_record.statement_line_id:
                        try:
                            new_record._create_bank_statement_line(journal)
                            _logger.info(f"Created transaction and statement line for EntryId: {entry_id}")
                        except Exception as stmt_error:
                            _logger.warning(f"Failed to create statement line for EntryId {entry_id}: {stmt_error}")
                    elif not journal:
                        _logger.warning(f"No journal found for account {record.get('my_bank_id')}, skipping statement line creation")

                    # Add to existing set to prevent duplicates in the same batch
                    existing_entry_ids_with_account.add(record_signature)
                except Exception as create_error:
                    _logger.error("Failed to create record with EntryId %s: %s", entry_id, create_error)
                    skipped_count += 1

            _logger.info(
                f"Transaction processing completed: {created_count} new records created, {skipped_count} duplicates skipped")

            # Show notification to user
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'BOG Transaction Import',
                    'message': f'{created_count} new transactions created, {skipped_count} duplicates skipped',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error("Failed to process records: %s", e)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to process records: {str(e)}',
                    'type': 'danger',
                    'sticky': True,
                }
            }


#exchange rate maq gakomentarebuli mere gasasworebeli iqneba


class TBCMovementsWizard(models.TransientModel):
    _name = 'tbc.movements.wizard'
    _description = 'TBC Movements Wizard'

    fromdate = fields.Date(string='პერიოდის დასაწყისი')
    todate = fields.Date(string='პერიოდის დასასრული')
    currency = fields.Selection([
        ('GEL', 'GEL'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('RUB', 'RUB'),
        ('GBP', 'GBP'),
    ], string='ვალუტა', default='GEL', required=True)

    company_id = fields.Many2one('res.company', string='Company')
    selected_bank_account_id = fields.Many2one(
        'res.partner.bank',
        string='აირჩიეთ ბანკის ანგარიში',
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            # Fetch bank accounts related to the selected company
            bank_accounts = self.env['res.partner.bank'].search([('company_id', '=', self.company_id.id)])
            return {
                'domain': {'selected_bank_account_id': [('id', 'in', bank_accounts.ids)]}
            }
        else:
            return {
                'domain': {'selected_bank_account_id': []}
            }

    def _get_currency_rate_for_movement(self, currency_name, transaction_date):
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

    def _convert_to_gel_for_movement(self, amount, currency_name, transaction_date):
        """
        Convert amount from foreign currency to GEL using res.currency.rate (for TBC Movements)
        """
        if not amount or currency_name == 'GEL':
            return amount

        rate = self._get_currency_rate_for_movement(currency_name, transaction_date)
        converted_amount = amount / rate if rate else amount
        _logger.info(f"Converting {amount} {currency_name} to GEL: {converted_amount} (rate: {rate})")
        return converted_amount

    def _find_or_create_partner_for_movement(self, record_dict):
        """
        Find or create partner from TBC movement data.
        Priority: 1. Search by VAT (partner_tax_code), 2. Search by name (exact), 3. Search by name (fuzzy), 4. Create new only if VAT exists
        """
        partner_tax_code = record_dict.get('partnerTaxCode')
        partner_name = record_dict.get('partnerName')

        if not partner_name and not partner_tax_code:
            _logger.debug("No partner information found in TBC movement")
            return False

        # Step 1: Try to find by VAT (Tax Code) - highest priority
        if partner_tax_code:
            partner = self.env['res.partner'].search([('vat', '=', partner_tax_code)], limit=1)
            if partner:
                _logger.debug(f"Found existing partner by VAT: {partner.name} (VAT: {partner_tax_code})")
                return partner

        # Step 2: Try to find by exact name match
        if partner_name:
            partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
            if partner:
                _logger.debug(f"Found existing partner by exact name: {partner.name}")
                # Update VAT if partner found but VAT was missing
                if partner_tax_code and not partner.vat:
                    partner.write({'vat': partner_tax_code})
                    _logger.info(f"Updated partner {partner.name} with VAT: {partner_tax_code}")
                return partner

        # Step 3: Try to find by fuzzy name match (case insensitive)
        if partner_name:
            partner = self.env['res.partner'].search([('name', '=ilike', partner_name)], limit=1)
            if partner:
                _logger.debug(f"Found existing partner by fuzzy name: {partner.name}")
                # Update VAT if partner found but VAT was missing
                if partner_tax_code and not partner.vat:
                    partner.write({'vat': partner_tax_code})
                    _logger.info(f"Updated partner {partner.name} with VAT: {partner_tax_code}")
                return partner

        # Step 4: Only create new partner if we have VAT
        if partner_name and partner_tax_code:
            # Create partner only if we have VAT
            partner_vals = {
                'name': partner_name,
                'vat': partner_tax_code,
                'company_type': 'company',
            }
            partner = self.env['res.partner'].create(partner_vals)
            _logger.info(f"Created new partner from TBC movement: {partner.name} (VAT: {partner_tax_code})")
            return partner
        elif partner_name and not partner_tax_code:
            # Don't create partner without VAT - just log and return False
            _logger.info(f"Partner not found for name '{partner_name}' without VAT - skipping creation to avoid duplicates")
            return False

        return False

    def _find_or_create_journal(self, account_number, currency='GEL'):
        """
        Find or create bank journal matching the account number and currency (same logic as BOG).
        Account number format: GE29BG0000000586405640
        Creates separate journals for each currency with format: GE29BG0000000586405640GEL
        Sets currency_id to the appropriate currency for proper filtering
        """
        if not account_number:
            _logger.warning("No account number provided")
            return False

        # Clean account number (remove spaces and any existing currency suffix)
        clean_acc_number = account_number.replace(' ', '')
        for curr in ['GEL', 'USD', 'EUR', 'RUB', 'GBP']:
            clean_acc_number = clean_acc_number.replace(curr, '')

        # Build full account identifier with currency
        full_account_with_currency = f"{clean_acc_number}{currency}"

        # Get currency record
        currency_record = self.env['res.currency'].search([('name', '=', currency)], limit=1)
        if not currency_record:
            _logger.error(f"Currency '{currency}' not found in the system")
            return False

        # Step 1: Try to find existing journal by full account number with currency and currency_id
        journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('name', '=', full_account_with_currency),
            ('currency_id', '=', currency_record.id)
        ], limit=1)

        if journal:
            _logger.debug(f"Found existing journal for account {full_account_with_currency}: {journal.name}")
            return journal

        # Step 2: Search in res.partner.bank for matching account (without currency suffix)
        bank_account = self.env['res.partner.bank'].search([
            ('acc_number', '=', clean_acc_number)
        ], limit=1)

        # Step 3: Create new bank journal with currency in name and currency_id
        journal_name = full_account_with_currency  # Full account number with currency
        journal_code = f"BNK{clean_acc_number[-6:]}{currency[:2]}"  # Use last 6 digits + currency code

        # Ensure unique code
        existing_code = self.env['account.journal'].search([('code', '=', journal_code)], limit=1)
        if existing_code:
            journal_code = f"BNK{clean_acc_number[-8:]}{currency[:2]}"  # Try with 8 chars

        journal_vals = {
            'name': journal_name,
            'code': journal_code,
            'type': 'bank',
            'bank_account_id': bank_account.id if bank_account else False,
            'currency_id': currency_record.id,
        }

        try:
            journal = self.env['account.journal'].create(journal_vals)
            _logger.info(f"Created new bank journal: {journal.name} (Code: {journal.code}, Currency: {currency})")
            return journal
        except Exception as e:
            _logger.error(f"Failed to create journal for account {clean_acc_number} with currency {currency}: {e}")
            return False

    def action_get_data(self):
        self.ensure_one()
        _logger.info("Fetching TBC data from API for dates: %s to %s, currency: %s", self.fromdate, self.todate, self.currency)

        # Use the selected bank to get the account number
        if not self.selected_bank_account_id:
            _logger.error("No bank selected.")
            return

        acc_number = self.selected_bank_account_id.acc_number.replace(' ', '')

        # Fetch data from the API
        data = self.get_data(self.fromdate, self.todate, self.currency, acc_number)

        if data:
            # Log raw TBC movements data - ALL RECORDS
            _logger.info("=" * 80)
            _logger.info(f"RAW TBC MOVEMENTS DATA - ALL {len(data)} RECORDS")
            _logger.info("=" * 80)

            # Log each movement record with key fields
            for i, record in enumerate(data, start=1):
                movement_id = record.get('movementId', 'N/A')
                debit_credit = record.get('debitCredit', 'N/A')
                value_date = record.get('valueDate', 'N/A')
                amount = record.get('amount', 0)
                currency = record.get('currency', 'N/A')
                description = record.get('description', 'N/A')
                partner_name = record.get('partnerName', 'N/A')
                operation_code = record.get('operationCode', 'N/A')

                _logger.info(
                    f"Record {i}/{len(data)}: "
                    f"MovementID={movement_id}, "
                    f"Date={value_date}, "
                    f"DebitCredit={debit_credit}, "
                    f"Amount={amount}, "
                    f"Currency={currency}, "
                    f"OperationCode={operation_code}, "
                    f"Partner={partner_name}, "
                    f"Description={description}"
                )

            _logger.info("=" * 80)
            _logger.info(f"VERIFICATION: Logged all {len(data)} TBC movement records")
            _logger.info("=" * 80)

            # Convert response data to DataFrame
            df = pd.json_normalize(data)
            _logger.info("Data converted to DataFrame with %d rows.", df.shape[0])

            created_count = 0
            skipped_count = 0

            for index, record in df.iterrows():
                record_dict = record.to_dict()  # Convert the row to a dictionary for logging
                _logger.debug("Processing movement record from row %d: %s", index, record_dict)

                try:
                    # Step 1: Find or create partner
                    partner = self._find_or_create_partner_for_movement(record_dict)

                    # Step 2: Create movement record with partner and bank account (amounts stay in original currency)
                    movement_vals = {
                        'movement_id': record_dict.get('movementId', False),
                        'external_payment_id': record_dict.get('externalPaymentId', False),
                        'debit_credit': record_dict.get('debitCredit', False),
                        'value_date': record_dict.get('valueDate', False),
                        'description': record_dict.get('description', False),
                        'amount': float(record_dict.get('amount', 0)),  # Keep original amount
                        'currency': record_dict.get('currency', False),  # Keep original currency
                        'account_number': record_dict.get('accountNumber', False),
                        'account_name': record_dict.get('accountName', False),
                        'additional_information': record_dict.get('additionalInformation', False),
                        'document_date': record_dict.get('documentDate', False),
                        'document_number': record_dict.get('documentNumber', False),
                        'partner_account_number': record_dict.get('partnerAccountNumber', False),
                        'partner_name': record_dict.get('partnerName', False),
                        'partner_tax_code': record_dict.get('partnerTaxCode', False),
                        'taxpayer_code': record_dict.get('taxpayerCode', False),
                        'taxpayer_name': record_dict.get('taxpayerName', False),
                        'operation_code': record_dict.get('operationCode', False),
                        'partner_personal_number': record_dict.get('partnerPersonalNumber', False),
                        'partner_document_type': record_dict.get('partnerDocumentType', False),
                        'partner_document_number': record_dict.get('partnerDocumentNumber', False),
                        'parent_external_payment_id': record_dict.get('parentExternalPaymentId', False),
                        'status_code': record_dict.get('statusCode', False),
                        'transaction_type': record_dict.get('transactionType', False),
                        'get_account_movements_response_io_id': record_dict.get('GetAccountMovementsResponseIo_Id', False),
                        'my_bank_id': acc_number,
                        'partner_id': partner.id if partner else False,
                    }

                    new_movement = self.env['tbc.movements'].create(movement_vals)
                    created_count += 1

                    # Step 3: Find or create journal with currency
                    journal = self._find_or_create_journal(acc_number, self.currency)

                    # Step 4: Auto-create statement line (conversion happens here)
                    if journal and not new_movement.statement_line_id:
                        try:
                            new_movement._create_bank_statement_line_with_journal(journal)
                            _logger.info(f"Created TBC movement and statement line for Movement ID: {record_dict.get('movementId')}")
                        except Exception as stmt_error:
                            _logger.warning(f"Failed to create statement line for Movement ID {record_dict.get('movementId')}: {stmt_error}")
                    elif not journal:
                        _logger.warning(f"No journal found for TBC account {acc_number}, skipping statement line creation")

                except Exception as e:
                    _logger.error("Failed to process TBC movement record at row %d: %s", index, str(e))
                    skipped_count += 1

            _logger.info(f"TBC Movement processing completed: {created_count} new records created, {skipped_count} failed")

            # Show notification to user
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'TBC Movement Import',
                    'message': f'{created_count} new movements created, {skipped_count} failed',
                    'type': 'success',
                    'sticky': False,
                }
            }

        else:
            _logger.warning("No data received from TBC API.")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Warning',
                    'message': 'No data received from TBC API',
                    'type': 'warning',
                    'sticky': False,
                }
            }

    def get_data(self, fromdate, todate, currency, acc_number):
        url = 'http://tfs.fmgsoft.ge:7780/API/FMGSoft/TBC_Movements'
        user = '206103722_GAS'
        pass_ = 'GasFmg123!!!'
        keycode = 'wqA04wDw'

        data = {
            'DateFrom': fromdate,
            'DateTo': todate,
            'AccountNumber': acc_number,
            'User': user,
            'Pass': pass_,
            'KeyCode': keycode,
            'Currency': currency
        }

        _logger.info("Sending request to API: %s", data)
        response = requests.post(url, data=data)

        if response.status_code == 200:
            response_data = response.json()
            _logger.info("API response received successfully.")

            # Log raw response from TBC API
            _logger.info("=" * 80)
            _logger.info("RAW RESPONSE FROM TBC API")
            _logger.info("=" * 80)
            _logger.info("Full response data: %s", response_data)
            _logger.info("=" * 80)

            return response_data.get('Data', None)
        else:
            _logger.error("Error fetching data from API: %s, Message: %s", response.status_code, response.text)
            return None



import base64
import fitz  # PyMuPDF
import pandas as pd
import re
import logging
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class TBCAccountStatementWizard(models.TransientModel):
    _name = 'tbc.account.statement.wizard'
    _description = 'Import Bank Statement from PDF'

    file = fields.Binary(string='Select PDF File', required=True)
    file_name = fields.Char(string='File Name')

    def action_import_statement(self):
        """Process the uploaded PDF file and create movements."""
        if not self.file:
            _logger.warning("No PDF file uploaded.")
            raise UserError(_('Please upload a PDF file.'))

        try:
            # Open the PDF file from binary data
            pdf_data = base64.b64decode(self.file)
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            text = ""
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text()
                _logger.debug("Extracted text from page %d: %s", page_num, page_text)
                text += page_text

            # Clean and process text
            text = text.strip().replace('\n', ' ')
        except Exception as e:
            _logger.error("Failed to read PDF file: %s", str(e))
            raise UserError(_('Error processing the PDF file.'))

        # Extract the first Bank ID from the text
        bank_id = self.extract_first_bank_id(text)
        _logger.info("Extracted Bank ID: %s", bank_id)

        # Call the parsing function
        df = self.parse_bank_statement(text)
        _logger.info("Parsed DataFrame: %s", df.to_dict(orient='records'))

        # Create movements based on the parsed DataFrame
        for _, row in df.iterrows():
            try:
                movement = self.env['tbc.movements'].create({
                    'movement_id': row['Identification Code'] or False,
                    'external_payment_id': False,
                    'debit_credit': '1' if row['Type'] == 'Paid In' else '0',
                    'value_date': row['Date'],
                    'description': row['Purpose'],
                    'amount': row['Amount (GEL)'],
                    'currency': 'GEL',  # Adjust currency as needed
                    'additional_information': row['Purpose'],
                    'partner_account_number': row['Bank ID'],  # Bank ID from DataFrame
                    'account_number': bank_id,  # First extracted Bank ID
                })

                _logger.info(
                    "Created movement: ID=%s, Amount=%s, Description=%s",
                    movement.movement_id, movement.amount, movement.description
                )
            except Exception as e:
                _logger.error(
                    "Failed to create movement for row %s: %s", row.to_dict(), str(e)
                )

    def extract_first_bank_id(self, text):
        """Extract the first Bank ID from the given text."""
        # Pattern to match the Bank ID format: GE + 2 digits + 2 letters + 16 digits
        bank_id_pattern = r'\bGE\d{2}[A-Z]{2}\d{16}\b'

        # Search for the first occurrence of the Bank ID
        match = re.search(bank_id_pattern, text)

        if match:
            bank_id = match.group(0)
            _logger.info("First Bank ID extracted: %s", bank_id)
            return bank_id
        else:
            _logger.warning("No Bank ID found.")
            return None

    def parse_bank_statement(self, text):
        """Parse the bank statement from the provided text."""
        split_text = re.split(
            r'გასული თანხა Paid Out\s+შემოსული თანხა Paid In\s+ბალანსი Balance',
            text,
            maxsplit=1
        )

        data = {
            "Date": [],
            "Purpose": [],
            "Identification Code": [],
            "Bank Code": [],
            "Bank ID": [],
            "Amount (GEL)": [],
            "Type": [],
            "Balance (GEL)": []
        }

        # Find the opening balance
        balance_pattern = r'საწყისი ნაშთი / Opening Balance\s+([\d,.]+)'
        balance_match = re.search(balance_pattern, text)
        starting_balance = float(balance_match.group(1).replace(',', '')) if balance_match else 0.0
        previous_balance = starting_balance

        if len(split_text) > 1:
            transactions_part = split_text[1].strip()

            transaction_pattern = (
                r'(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,.]+(?:\.\d{2})?)\s+([\d,.]+(?:\.\d{2})?)'
            )
            matches = re.findall(transaction_pattern, transactions_part)

            for match in matches:
                date_str = match[0]
                date = datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
                description = match[1]
                amount = float(match[2].replace(',', ''))
                current_balance = float(match[3].replace(',', ''))

                description_parts = [
                    part.strip() for part in re.split(r',\s*', description) if part.strip()
                ]

                purpose = description_parts[0] if description_parts else None
                bank_code = re.search(r'([A-Z]{4,}(?:\d{2})?)', description)
                bank_code = bank_code.group(1) if bank_code else None

                bank_id = re.search(r'([A-Z]{2}\d{2}[A-Z]{2}\d{16})', description)
                bank_id = bank_id.group(1) if bank_id else None

                id_code_match = re.search(r'\b(\d{9})\b', description)
                identification_code = id_code_match.group(1) if id_code_match else None

                transaction_type = "Paid In" if current_balance > previous_balance else "Paid Out"

                data["Date"].append(date)
                data["Purpose"].append(purpose)
                data["Identification Code"].append(identification_code)
                data["Bank Code"].append(bank_code)
                data["Bank ID"].append(bank_id)
                data["Amount (GEL)"].append(abs(amount))
                data["Type"].append(transaction_type)
                data["Balance (GEL)"].append(current_balance)

                previous_balance = current_balance

        df = pd.DataFrame(data)
        _logger.info("Final DataFrame created with %d rows.", len(df))
        return df




import base64
import re
import fitz  # PyMuPDF
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class BogStatementPDFWizard(models.TransientModel):
    _name = 'bog.statement.pdf.wizard'
    _description = 'BOG Statement PDF Wizard'

    pdf_file = fields.Binary(string="Upload PDF File", required=True)
    pdf_filename = fields.Char(string="Filename")

    def extract_and_process_transactions(self):
        if not self.pdf_file:
            raise UserError(_("Please upload a PDF file."))

        # Decode the PDF file
        pdf_data = base64.b64decode(self.pdf_file)

        # Open the PDF file using PyMuPDF
        with fitz.open(stream=pdf_data, filetype="pdf") as doc:
            text = ""
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                text += page.get_text("text")

        # Clean up the text
        text = re.sub(r'\s+', ' ', text).strip()

        # Extract transactions
        transactions = self.extract_transactions(text)
        account_number = self.extract_account_number(text)

        # Create records for each transaction
        for transaction_data in transactions:
            date_str = transaction_data["Date"]
            day, month, year = date_str.split('.')
            formatted_date = f"{year}-{month}-{day}"
            debit_credit = transaction_data["Debit/Credit"]
            entry_amount_credit = transaction_data["Amount"] if debit_credit == 'Credit' else 0.0
            entry_amount_debit = transaction_data["Amount"] if debit_credit == 'Debit' else 0.0# Convert to YYYY-MM-DD format

            transaction_record = self.env['tbc_payment_integration.tbc_payment_integration'].create({
                "entry_date": formatted_date,
                'entry_id': transaction_data["Transaction ID"],
                'sender_details_name': transaction_data["Sender/Receiver"],
                'entry_amount_credit': entry_amount_credit,
                'entry_amount_debit': entry_amount_debit,
                'entry_amount': transaction_data["Amount"],
                'doc_comment': transaction_data["Description"],
                'my_bank_id': account_number,  # New field
            })

            # Log the created transaction
            _logger.info(f"Created transaction: ID={transaction_record.entry_id}, "
                         f"Date={transaction_record.entry_date}, "
                         f"Amount={transaction_record.entry_amount}, "
                         f"Account Number={transaction_record.entry_account_number}")

    def extract_transactions(self, text):
        pattern = r"""
            (?P<date>\d{2}\.\d{2}\.\d{4})        # Date in DD.MM.YYYY format
            \s+
            (?P<transaction_id>\d+)              # Transaction ID (digits only)
            \s+
            (?P<sender_receiver>.*?)             # Sender/Receiver (non-greedy)
            \s+
            (?P<amount>\d{1,3}(?:,\d{3})*\.\d{2}) # Amount
            \s+
            (?P<description>.*?)                 # Description (non-greedy)
            (?=\d{2}\.\d{2}\.\d{4}|\Z)           # Lookahead for next date or end
        """
        matches = re.finditer(pattern, text, re.VERBOSE | re.DOTALL)

        transactions = []
        for match in matches:
            description = match.group("description").strip()
            account_number = self.extract_account_number(description)  # Extract account number
            debit_credit = 'Credit' if 'გადახდა' in description else 'Debit'

            transaction = {
                "Date": match.group("date"),
                "Transaction ID": match.group("transaction_id"),
                "Sender/Receiver": match.group("sender_receiver").strip(),
                "Amount": float(match.group("amount").replace(",", "")),
                "Description": description,
                "Account Number": account_number or "",
                "Debit/Credit": debit_credit,            }
            transactions.append(transaction)

        return transactions

    def extract_account_number(self, text):
        """
        Extracts the 22-character Georgian IBAN without the 'GEL' suffix.

        Args:
            text (str): The input text containing the IBAN.

        Returns:
            str or None: The extracted account number or None if not found.
        """
        match = re.search(r"\b(GE\d{2}[A-Z]{2}\d{16})(?=GEL)", text)
        return match.group(1) if match else None











