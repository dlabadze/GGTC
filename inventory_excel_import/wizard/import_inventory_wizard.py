import base64
import io
import pandas as pd
from datetime import datetime, time
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ImportInventoryWizard(models.TransientModel):
    _name = 'inventory.excel.import.wizard'
    _description = 'Import Inventory from Excel and Backdate'

    excel_file = fields.Binary(string="Excel File", required=True)
    file_name = fields.Char(string="File Name")
    target_date = fields.Date(string="Inventory Date", required=True, default=fields.Date.context_today,
                              help="The date you want the inventory adjustment and stock moves to reflect.")

    def action_import_inventory(self):
        self.ensure_one()

        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))

        try:
            # Decode the uploaded file
            file_content = base64.b64decode(self.excel_file)
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Clean column names
            df.columns = df.columns.astype(str).str.strip()
            
            expected_columns = ['product_id/id', 'location_id/id', 'რაოდ']
            for col in expected_columns:
                if col not in df.columns:
                    raise UserError(_("Missing required column in Excel: %s") % col)

            # Combine user's selected date with time 00:00:00
            target_datetime = datetime.combine(self.target_date, time(0, 0, 0))
            
            success_count = 0
            error_count = 0
            
            # Context with forced accounting period if needed
            ctx = dict(self.env.context, force_period_date=target_datetime)
            
            for index, row in df.iterrows():
                try:
                    product_ext_id = str(row.get('product_id/id', '')).strip()
                    location_ext_id = str(row.get('location_id/id', '')).strip()
                    qty = float(row.get('რაოდ', 0.0))
                    
                    if not product_ext_id or product_ext_id == 'nan' or not location_ext_id or location_ext_id == 'nan':
                        continue
                        
                    # Find product via external ID (ir.model.data)
                    product = self.env.ref(product_ext_id, raise_if_not_found=False)
                    if not product or product._name != 'product.product':
                        _logger.warning("Row %s: Product %s not found. Skipping.", index, product_ext_id)
                        error_count += 1
                        continue
                        
                    # Find location via external ID
                    location = self.env.ref(location_ext_id, raise_if_not_found=False)
                    if not location or location._name != 'stock.location':
                        _logger.warning("Row %s: Location %s not found. Skipping.", index, location_ext_id)
                        error_count += 1
                        continue
                    
                    # Find or create the stock.quant
                    quant = self.env['stock.quant'].with_context(ctx).search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', location.id),
                    ], limit=1)
                    
                    if not quant:
                        quant = self.env['stock.quant'].with_context(ctx).create({
                            'product_id': product.id,
                            'location_id': location.id,
                        })
                    
                    # Set the counted quantity
                    quant.with_context(ctx).inventory_quantity = qty
                    
                    # Apply the adjustment
                    quant.with_context(ctx).action_apply_inventory()
                    
                    # Backdate the generated stock moves via SQL to bypass ORM readonly block
                    moves = self.env['stock.move'].search([
                        ('product_id', '=', product.id),
                        ('location_dest_id', '=', location.id),
                        ('is_inventory', '=', True),
                        ('state', '=', 'done')
                    ], order='date desc', limit=1)
                    
                    for move in moves:
                        self.env.cr.execute("UPDATE stock_move SET date = %s WHERE id = %s", (target_datetime, move.id))
                        self.env.cr.execute("UPDATE stock_move_line SET date = %s WHERE move_id = %s", (target_datetime, move.id))
                        self.env.cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE stock_move_id = %s", (target_datetime, move.id))

                    success_count += 1
                    
                except Exception as e:
                    _logger.error("Error on row %s (%s): %s", index, product_ext_id, e)
                    error_count += 1

            message = _("Successfully imported and backdated %s inventory lines to %s.") % (success_count, self.target_date)
            if error_count > 0:
                message += _("\nFailed to import %s lines (check server logs for details).") % error_count

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Complete'),
                    'message': message,
                    'type': 'success' if error_count == 0 else 'warning',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_("Error processing Excel file: %s") % str(e))
