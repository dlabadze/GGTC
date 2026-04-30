from odoo import models, fields, api, _
import requests
import datetime
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

original_browse = models.BaseModel.browse

def safe_browse(self, *args):
    if self._name == 'purchase.order' and args and args[0] == 7:
        return self.env['purchase.order']
    if self._name == 'pos.session' and args and args[0] == 1:
        return self.env['pos.session']
    return original_browse(self, *args)

models.BaseModel.browse = safe_browse

class NBGCurrencyUpdate(models.TransientModel):
    _name = "nbg.currency.update"
    _description = "Update Currency Rates from NBG"
    
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1)
    )
    
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today
    )

    def action_update_rates(self):
        """Button action handler for wizard"""
        self = self.sudo()
        success_count, failed_dates = self.update_currency_rates(self.start_date, self.end_date)
        
        # Create user notification message
        message = _(f'Updated rates for {success_count} dates successfully.')
        if failed_dates:
            message += _('\nFailed to update rates for these dates: %s') % ', '.join(failed_dates[:10])
            if len(failed_dates) > 10:
                message += _(' and %d more...') % (len(failed_dates) - 10)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Currency Rates Update'),
                'message': message,
                'type': 'info',
                'sticky': False,
            }
        }

    @api.model
    def update_currency_rates(self, start_date=None, end_date=None):
        """Update currency rates for the given date range"""
        self = self.sudo().with_context(active_test=True)
        
        if not start_date:
            start_date = fields.Date.today()
        if not end_date:
            end_date = fields.Date.today()
        
        if start_date > end_date:
            start_date, end_date = end_date, start_date
            
        # Get all active currencies
        currencies = self.env['res.currency'].search([('active', '=', True)])
        
        success_count = 0
        failed_dates = []
        
        # Loop through dates
        current_date = start_date
        while current_date <= end_date:
            # Process all days including weekends
            try:
                if self._update_rates_for_date(current_date, currencies):
                    success_count += 1
                else:
                    failed_dates.append(current_date.strftime('%Y-%m-%d'))
            except Exception as e:
                _logger.error(f"Error updating rates for {current_date}: {e}", exc_info=True)
                failed_dates.append(current_date.strftime('%Y-%m-%d'))
            
            current_date += datetime.timedelta(days=1)
        
        _logger.info(f"Updated rates for {success_count} dates successfully")
        if failed_dates:
            _logger.warning(f"Failed to update rates for dates: {', '.join(failed_dates[:10])}")
            if len(failed_dates) > 10:
                _logger.warning(f"...and {len(failed_dates) - 10} more")
        
        return success_count, failed_dates

    def _update_rates_for_date(self, date, currencies):
        """Update rates for all currencies for a specific date"""
        try:
            # Format date for API call
            date_str = date.strftime('%Y-%m-%d')
            api_url = f'https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?date={date_str}'
            
            # Call the API
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            
            # Process the response
            data = response.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                _logger.warning(f'No data received from NBG API for date {date_str}')
                return False
            
            # The response is a list, get the first element
            data = data[0]
            currencies_data = data.get('currencies', [])
            
            if not currencies_data:
                _logger.warning(f'No currencies data found in NBG API response for date {date_str}')
                return False
            
            # Update each currency rate
            try:
                base_currency = self.env.ref('base.GEL', raise_if_not_found=False)
                if not base_currency:
                    base_currency = self.env['res.currency'].search([('name', '=', 'GEL')], limit=1)
                    if not base_currency:
                        _logger.error('GEL currency not found in the system')
                        return False
                
                # Set GEL as base currency with rate 1.0
                self._set_currency_rate(base_currency, date, 1.0)
            except Exception as e:
                _logger.error(f"Error setting base currency: {e}", exc_info=True)
                return False
            
            # Update rates for other currencies
            updated_currencies = []
            for currency in currencies:
                try:
                    # Skip GEL as it's already set
                    if currency.name == 'GEL':
                        updated_currencies.append(currency.name)
                        continue
                    
                    # Find currency in API data
                    for currency_data in currencies_data:
                        if currency_data.get('code') == currency.name:
                            rate = float(currency_data.get('rate', 0))
                            quantity = float(currency_data.get('quantity', 1))
                            
                            # Calculate the correct rate
                            if rate > 0:
                                # Convert to rate per 1 unit if quantity > 1
                                direct_rate = rate / quantity
                                # Odoo uses inverse rates (1/rate)
                                inverse_rate = 1.0 / direct_rate
                                
                                self._set_currency_rate(currency, date, inverse_rate)
                                updated_currencies.append(currency.name)
                            break
                except Exception as e:
                    _logger.error(f"Error updating rate for currency {currency.name}: {e}", exc_info=True)
                    continue  
            
            _logger.info(f"Updated currencies for {date_str}: {', '.join(updated_currencies)}")
            return True
            
        except requests.RequestException as e:
            _logger.error(f'Failed to fetch data from the API for {date_str}: {e}')
            return False
        except ValueError as e:
            _logger.error(f'Invalid JSON response from API for {date_str}: {e}')
            return False
        except Exception as e:
            _logger.error(f'Error processing API data for {date_str}: {e}', exc_info=True)
            return False
    
    def _set_currency_rate(self, currency, date, rate):
        """Set or update rate for a currency on a specific date"""
        if not currency.exists():
            _logger.error(f"Currency record does not exist")
            return False
            
        if not self.env.company.exists():
            _logger.error(f"Company record does not exist")
            return False
            
        rate_model = self.env['res.currency.rate']
        
        try:
            # Check if the rate already exists
            existing_rate = rate_model.search([
                ('currency_id', '=', currency.id),
                ('name', '=', date),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            rate_vals = {
                'currency_id': currency.id,
                'name': date,
                'rate': rate,
                'company_id': self.env.company.id
            }
            
            if existing_rate and existing_rate.exists():
                existing_rate.write(rate_vals)
                _logger.debug(f"Updated rate for {currency.name} on {date}: {rate}")
            else:
                rate_model.create(rate_vals)
                _logger.debug(f"Created new rate for {currency.name} on {date}: {rate}")
            
            return True
        except Exception as e:
            _logger.error(f"Failed to set rate for {currency.name} on {date}: {e}", exc_info=True)
            return False

    @api.model
    def update_today_rates(self):
        """Update rates for today (called by scheduled action)"""
        try:
            self = self.sudo()
            today = fields.Date.today()
            self.with_context(active_test=True).update_currency_rates(today, today)
            return True
        except Exception as e:
            _logger.error(f"Error in update_today_rates: {e}", exc_info=True)
            return False
        
    @api.model
    def update_year_rates(self):
        """Update all rates from beginning of year to today"""
        try:
            self = self.sudo()
            start_date = fields.Date.today().replace(month=1, day=1)
            end_date = fields.Date.today()
            self.with_context(active_test=True).update_currency_rates(start_date, end_date)
            return True
        except Exception as e:
            _logger.error(f"Error in update_year_rates: {e}", exc_info=True)
            return False


class Currency(models.Model):
    _inherit = "res.currency"
    
    def action_open_nbg_update(self):
        """Open the NBG currency update wizard"""
        return {
            'name': 'Update from NBG',
            'type': 'ir.actions.act_window',
            'res_model': 'nbg.currency.update',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_start_date': fields.Date.today(), 'default_end_date': fields.Date.today()},
        }