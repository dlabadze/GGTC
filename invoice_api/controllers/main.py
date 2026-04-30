import json
import logging
from datetime import datetime, timedelta
import calendar
import odoo
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class GasInvoiceAPI(http.Controller):

    # Debug route to test basic routing
    @http.route('/api/debug', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def debug_route(self, **kwargs):
        return Response(json.dumps({
            'success': True,
            'message': 'Debug route is working!',
            'method': request.httprequest.method,
            'path': request.httprequest.path,
            'database': request.env.cr.dbname if request.env and request.env.cr else 'No DB',
            'params': dict(kwargs)
        }), headers={'Content-Type': 'application/json'})

    # Split the routes to better handle parameters
    @http.route('/api/create_invoice', type='http', auth='public', methods=['POST'], csrf=False)
    def create_invoice_default(self, **kwargs):
        """Create invoice in current/default database"""
        try:
            # Get JSON data from request body
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data.decode('utf-8'))
            else:
                return Response(json.dumps({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }), headers={'Content-Type': 'application/json'}, status=400)

            return self._create_invoice_current_db(data)

        except json.JSONDecodeError:
            return Response(json.dumps({
                'success': False,
                'error': 'Invalid JSON format'
            }), headers={'Content-Type': 'application/json'}, status=400)
        except Exception as e:
            _logger.error(f"Error creating invoice: {str(e)}")
            return Response(json.dumps({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }), headers={'Content-Type': 'application/json'}, status=500)

    @http.route('/api/create_invoice/<string:db_name>', type='http', auth='public', methods=['POST'], csrf=False)
    def create_invoice_db(self, db_name, **kwargs):
        """Create invoice in specified database"""
        try:
            # Get JSON data from request body
            if request.httprequest.content_type == 'application/json':
                data = json.loads(request.httprequest.data.decode('utf-8'))
            else:
                return Response(json.dumps({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }), headers={'Content-Type': 'application/json'}, status=400)

            # Handle different database contexts
            if db_name != request.env.cr.dbname:
                return self._create_invoice_in_database(db_name, data)
            else:
                return self._create_invoice_current_db(data)

        except json.JSONDecodeError:
            return Response(json.dumps({
                'success': False,
                'error': 'Invalid JSON format'
            }), headers={'Content-Type': 'application/json'}, status=400)
        except Exception as e:
            _logger.error(f"Error creating invoice in {db_name}: {str(e)}")
            return Response(json.dumps({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }), headers={'Content-Type': 'application/json'}, status=500)

    def _create_invoice_in_database(self, db_name, data):
        """Create invoice in specified database"""
        try:
            # Validate database exists and is accessible
            try:
                registry = odoo.registry(db_name)
            except Exception as e:
                return Response(json.dumps({
                    'success': False,
                    'error': f'Database {db_name} not accessible: {str(e)}'
                }), headers={'Content-Type': 'application/json'}, status=400)

            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                # Validate required fields
                validation_response = self._validate_invoice_data(data)
                if validation_response:
                    return validation_response

                # Create the invoice in specified database
                invoice_id = self._create_customer_invoice_with_env(env, data)

                # Get invoice number
                invoice = env['account.move'].browse(invoice_id)

                # Commit the transaction
                cr.commit()

                return Response(json.dumps({
                    'success': True,
                    'data': {
                        'message': 'Invoice created successfully',
                        'invoice_id': invoice_id,
                        'invoice_number': invoice.name,
                        'database': db_name
                    }
                }), headers={'Content-Type': 'application/json'})

        except ValidationError as e:
            return Response(json.dumps({
                'success': False,
                'error': f'Validation error: {str(e)}'
            }), headers={'Content-Type': 'application/json'}, status=400)
        except Exception as e:
            _logger.error(f"Error creating invoice in database {db_name}: {str(e)}")
            return Response(json.dumps({
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }), headers={'Content-Type': 'application/json'}, status=500)

    def _create_invoice_current_db(self, data):
        """Create invoice in current database context"""
        try:
            # Validate required fields
            validation_response = self._validate_invoice_data(data)
            if validation_response:
                return validation_response

            # Create the invoice
            invoice_id = self._create_customer_invoice_with_env(request.env, data)

            # Get invoice number
            invoice = request.env['account.move'].sudo().browse(invoice_id)

            return Response(json.dumps({
                'success': True,
                'data': {
                    'message': 'Invoice created successfully',
                    'invoice_id': invoice_id,
                    'invoice_number': invoice.name,
                    'database': request.env.cr.dbname
                }
            }), headers={'Content-Type': 'application/json'})

        except ValidationError as e:
            return Response(json.dumps({
                'success': False,
                'error': f'Validation error: {str(e)}'
            }), headers={'Content-Type': 'application/json'}, status=400)

    def _validate_invoice_data(self, data):
        """Validate invoice data and return error response if invalid"""
        # Validate required fields
        required_fields = ['customer_name', 'customer_phone', 'customer_id', 'invoice_date', 'quantity_m3']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            return Response(json.dumps({
                'success': False,
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }), headers={'Content-Type': 'application/json'}, status=400)

        # Validate invoice_date format
        try:
            datetime.strptime(data['invoice_date'], '%Y-%m-%d')
        except ValueError:
            return Response(json.dumps({
                'success': False,
                'error': 'Invalid invoice_date format. Use YYYY-MM-DD'
            }), headers={'Content-Type': 'application/json'}, status=400)

        return None  # No validation errors

    def _calculate_last_day_next_month(self, date_string):
        """Calculate the last day of the next month based on input date"""
        return date_string

    def _get_business_due_date(self, env, start_date, days_to_add):
        """
        Calculate due date by adding calendar days, then adjusting if final date
        falls on weekend or holiday
        """
        if days_to_add <= 0:
            return start_date

        # Convert string date to date object if needed
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        # Step 1: Add the calendar days
        due_date = start_date + timedelta(days=days_to_add)

        _logger.info(f"Calculating due date: {start_date} + {days_to_add} calendar days = {due_date}")

        # Step 2: If due date falls on weekend or holiday, move to next business day
        original_due_date = due_date
        while self._is_weekend_or_holiday(env, due_date):
            _logger.debug(f"Due date {due_date.strftime('%A %Y-%m-%d')} is weekend/holiday, moving to next day")
            due_date += timedelta(days=1)

        if due_date != original_due_date:
            _logger.info(f"Adjusted due date from {original_due_date} to {due_date} (next business day)")
        else:
            _logger.info(f"Due date {due_date} is already a business day")

        return due_date

    def _is_weekend_or_holiday(self, env, date):
        """
        Check if date is weekend or holiday
        """
        # Check weekend (Saturday=5, Sunday=6)
        if date.weekday() >= 5:
            return True

        # Check holiday from resource.calendar.leaves
        return self._is_holiday(env, date)

    def _is_holiday(self, env, date):
        """
        Check if a date is a public holiday using resource.calendar.leaves
        """
        try:
            # Convert date to datetime for comparison if it's a date object
            if hasattr(date, 'date'):
                check_date = date
                check_datetime = datetime.combine(date, datetime.min.time())
            else:
                check_date = date
                check_datetime = datetime.combine(date, datetime.min.time())

            # Search for public holidays that cover this date
            # We look for leaves that are either:
            # 1. Company-wide (no specific calendar_id or resource_id)
            # 2. Public holidays (holiday=True if the field exists)

            domain = [
                ('date_from', '<=', check_datetime),
                ('date_to', '>=', check_datetime),
                # Look for company-wide holidays (no specific resource assigned)
                ('resource_id', '=', False),
            ]

            # If the holiday field exists on resource.calendar.leaves, use it
            if 'holiday' in env['resource.calendar.leaves']._fields:
                domain.append(('holiday', '=', True))

            holidays = env['resource.calendar.leaves'].sudo().search(domain)

            if holidays:
                holiday_names = holidays.mapped('name')
                _logger.debug(f"Date {check_date} is a public holiday: {', '.join(holiday_names)}")
                return True

            # Additional check: look for leaves without resource_id but with calendar_id
            # that might represent company-wide holidays
            if not holidays:
                domain_calendar = [
                    ('date_from', '<=', check_datetime),
                    ('date_to', '>=', check_datetime),
                    ('calendar_id', '!=', False),
                    ('resource_id', '=', False),
                ]

                calendar_holidays = env['resource.calendar.leaves'].sudo().search(domain_calendar)
                if calendar_holidays:
                    holiday_names = calendar_holidays.mapped('name')
                    _logger.debug(f"Date {check_date} is a calendar holiday: {', '.join(holiday_names)}")
                    return True

            # Fallback: Check basic holidays if no resource.calendar.leaves found
            return self._is_basic_holiday(check_date)

        except Exception as e:
            _logger.warning(f"Error checking holiday for date {date}: {str(e)}")
            # Fallback to basic holiday check
            return self._is_basic_holiday(date if hasattr(date, 'month') else date.date())

    def _is_basic_holiday(self, date):
        """
        Fallback method for basic holiday checking
        """
        # Basic holidays - extend this list as needed for Georgian holidays
        basic_holidays = [
            (1, 1),   # New Year's Day
            (1, 2),   # New Year's Holiday
            (1, 7),   # Orthodox Christmas
            (3, 8),   # Women's Day
            (4, 9),   # Day of National Unity
            (5, 9),   # Victory Day
            (5, 12),  # Saint Andrew's Day
            (5, 26),  # Independence Day
            (8, 28),  # Assumption of Mary
            (10, 14), # Svetitskhovloba (Georgian Orthodox holiday)
            (11, 23), # Saint George's Day
            (12, 25), # Christmas Day
        ]

        return (date.month, date.day) in basic_holidays

    def _calculate_due_date_with_business_days(self, env, invoice_date, payment_term):
        """
        Calculate due date considering business days for payment terms
        """
        try:
            # Convert string date to date object if needed
            if isinstance(invoice_date, str):
                invoice_date = datetime.strptime(invoice_date, '%Y-%m-%d').date()

            # If no payment term, return invoice date
            if not payment_term:
                return invoice_date

            # Calculate due date based on payment term
            max_days = 0
            for line in payment_term.line_ids:
                if line.nb_days > max_days:
                    max_days = line.nb_days

            if max_days > 0:
                # Use business day calculation
                due_date = self._get_business_due_date(env, invoice_date, max_days)
            else:
                # Same day or past due
                due_date = invoice_date + timedelta(days=max_days)

            return due_date

        except Exception as e:
            _logger.warning(f"Error calculating due date with business days: {str(e)}")
            # Fallback to standard calculation
            if payment_term and payment_term.line_ids:
                max_days = max(line.nb_days for line in payment_term.line_ids)
                return invoice_date + timedelta(days=max_days)
            return invoice_date

    def _get_gas_transport_journal(self, env):
        """Find the journal with name 'გაზის ტრანსპორტირება'"""
        journal = env['account.journal'].sudo().search([
            ('name', '=', 'გაზის ტრანსპორტირება')
        ], limit=1)

        if not journal:
            raise ValidationError("Journal with name 'გაზის ტრანსპორტირება' not found")

        return journal

    def _get_gas_transport_product(self, env):
        """Find the product with name 'გაზის ტრანსპორტირება'"""
        product = env['product.product'].sudo().search([
            ('name', '=', 'გაზის ტრანსპორტირება')
        ], limit=1)

        if not product:
            raise ValidationError("Product with name 'გაზის ტრანსპორტირება' not found")

        return product

    def _get_payment_term_25_days(self, env):
        """Find the payment term with name '25 Days'"""
        payment_term = env['account.payment.term'].sudo().search([
            ('name', '=', '25 Days')
        ], limit=1)

        if not payment_term:
            raise ValidationError("Payment term with name '25 Days' not found")

        return payment_term

    def _create_customer_invoice_with_env(self, env, data):
        """Create customer invoice from API data using provided environment"""
        # Handle company selection if provided
        company_id = data.get('company_id')
        if company_id:
            company = env['res.company'].browse(company_id)
            if not company.exists():
                raise ValidationError(f"Invalid company_id: {company_id}")
            # Set company context
            env = env.with_company(company)

        # Find or create partner using customer_id as Tax ID
        partner = self._get_or_create_partner_with_env(env, data)

        # Calculate invoice date as last day of next month
        calculated_invoice_date = self._calculate_last_day_next_month(data['invoice_date'])

        # Get the gas transport journal
        journal = self._get_gas_transport_journal(env)

        # Get the gas transport product
        product = self._get_gas_transport_product(env)

        # Get the 25 days payment term
        payment_term = self._get_payment_term_25_days(env)

        # Calculate due date with business days logic
        calculated_due_date = self._calculate_due_date_with_business_days(
            env, calculated_invoice_date, payment_term
        )

        # Prepare invoice data
        invoice_vals = {
            'move_type': 'out_invoice',  # Customer invoice
            'partner_id': partner.id,
            'invoice_date': calculated_invoice_date,
            'invoice_date_due': calculated_due_date,  # Set calculated due date
            'journal_id': journal.id,  # Set the specific journal
            'invoice_payment_term_id': payment_term.id,  # Set 25 days payment term
            'ref': f"Tax ID: {data['customer_id']}",
            'invoice_line_ids': []
        }

        # Add company if specified
        if company_id:
            invoice_vals['company_id'] = company_id

        # Create invoice line for gas transportation service
        line_vals = {
            'product_id': product.id,  # Set the product ID
            'name': product.name,  # This will be auto-filled from product
            'quantity': float(data['quantity_m3']),
        }

        # Use product's list price if no custom price provided
        if 'unit_price' in data and data['unit_price']:
            line_vals['price_unit'] = float(data['unit_price'])
        else:
            # Use product's list price (lst_price field)
            line_vals['price_unit'] = product.lst_price

        invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

        # Create invoice
        invoice = env['account.move'].sudo().create(invoice_vals)

        _logger.info(f"Created invoice {invoice.name} with due date {invoice.invoice_date_due} (business day adjusted)")

        return invoice.id

    def _get_or_create_partner_with_env(self, env, data):
        """Find existing partner by Tax ID (vat field) or create new one using provided environment"""
        customer_id = data['customer_id']  # This will be used as Tax ID
        customer_name = data['customer_name']
        customer_phone = data['customer_phone']

        # Try to find existing partner by Tax ID (vat field)
        partner = env['res.partner'].sudo().search([
            ('vat', '=', customer_id)
        ], limit=1)

        if not partner:
            # Create new partner with Tax ID, name, and phone
            partner_vals = {
                'name': customer_name,
                'phone': customer_phone,
                'vat': customer_id,  # Store customer_id as Tax ID in vat field
                'is_company': True,
                'customer_rank': 1  # Mark as customer
            }
            partner = env['res.partner'].sudo().create(partner_vals)
        else:
            # Update existing partner info if needed
            update_vals = {}
            if partner.name != customer_name:
                update_vals['name'] = customer_name
            if partner.phone != customer_phone:
                update_vals['phone'] = customer_phone

            if update_vals:
                partner.write(update_vals)

        return partner

    # Legacy method for backward compatibility
    def _create_customer_invoice(self, data):
        """Legacy method - use _create_customer_invoice_with_env instead"""
        return self._create_customer_invoice_with_env(request.env, data)

    def _get_or_create_partner(self, data):
        """Legacy method - use _get_or_create_partner_with_env instead"""
        return self._get_or_create_partner_with_env(request.env, data)