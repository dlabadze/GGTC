from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_reprocess_stock_valuation(self):
        """
        Generic action to re-process valuation for the picking.
        Deletes existing valuation data and re-creates it using the picking's date.
        """
        processed_count = 0
        skipped_count = 0
        
        for picking in self:
            if picking.state != 'done':
                skipped_count += 1
                continue
            
            processed_count += 1

            # Determine the date to use (picking.date_done or picking.scheduled_date)
            valuation_date = picking.date_done or picking.scheduled_date or fields.Datetime.now()

            for move in picking.move_ids:
                if move.product_id.valuation != 'automated':
                    continue

                # 1. Find and delete existing valuation data
                valuation_layers = self.env['stock.valuation.layer'].search([('stock_move_id', '=', move.id)])
                for layer in valuation_layers:
                    if layer.account_move_id:
                        layer.account_move_id.button_draft()
                        layer.account_move_id.with_context(force_delete=True).unlink()
                    layer.sudo().unlink()

                # 2. Re-trigger valuation
                # We use the standard Odoo method if possible, but we want to control the date.
                # Standard method: move._account_entry_move()
                # However, _account_entry_move normally uses 'fields.Date.context_today(self)' or similar.
                
                # To be safe and generic, we will manually create the valuation layer and account move
                # similar to how stock_account does it, but ensuring the date is correct.
                
                # Create Stock Valuation Layer
                quantity = move.product_qty
                if move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
                    # Outgoing
                    value = -move.product_id.standard_price * quantity
                elif move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal':
                    # Incoming
                    value = move.product_id.standard_price * quantity
                else:
                    # Internal Transfer
                    # For internal transfers, Odoo usually creates layers if valuation accounts differ.
                    value = move.product_id.standard_price * quantity

                svl_vals = {
                    'product_id': move.product_id.id,
                    'quantity': quantity if move.location_dest_id.usage == 'internal' else -quantity,
                    'unit_cost': move.product_id.standard_price,
                    'value': value,
                    'company_id': move.company_id.id,
                    'stock_move_id': move.id,
                    'description': f"{picking.name} - {move.product_id.name} (Re-entry)",
                }
                new_layer = self.env['stock.valuation.layer'].sudo().create(svl_vals)
                
                # Update create_date via SQL because it's a log field
                self.env.cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE id = %s", (valuation_date, new_layer.id))

                # Create Account Move if needed
                if move.product_id.valuation == 'automated':
                    # Get accounts from standard Odoo method
                    accounts = move.product_id.product_tmpl_id.get_product_accounts()
                    
                    # Generic internal transfer account detection
                    if move.location_id.valuation_out_account_id and move.location_dest_id.valuation_in_account_id:
                        acc_src = move.location_id.valuation_out_account_id.id
                        acc_dest = move.location_dest_id.valuation_in_account_id.id
                    else:
                        # For internal, usually it moves between the same valuation account
                        # unless locations are configured differently.
                        acc_src = accounts.get('stock_valuation') and accounts['stock_valuation'].id
                        acc_dest = accounts.get('stock_valuation') and accounts['stock_valuation'].id

                    # For outgoing/incoming
                    if move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal':
                        # Incoming
                        acc_src = accounts.get('stock_input') and accounts['stock_input'].id
                    elif move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
                        # Outgoing
                        acc_dest = accounts.get('stock_output') and accounts['stock_output'].id

                    if not acc_src or not acc_dest:
                        continue

                    # If accounts are the same and it's internal, Odoo normally skips.
                    # But if we want to force re-entry as per doc, we allow it.
                    
                    journal_id = move.product_id.categ_id.property_stock_journal.id or picking.picking_type_id.warehouse_id.base_header_id.journal_id.id # fallback
                    if not journal_id:
                        # Try to find any stock journal
                        journal_id = self.env['account.journal'].search([('type', '=', 'general'), ('code', '=', 'STJ')], limit=1).id
                    
                    if not journal_id:
                        continue

                    move_vals = {
                        'ref': picking.name,
                        'date': valuation_date.date(),
                        'journal_id': journal_id,
                        'move_type': 'entry',
                        'stock_move_id': move.id,
                        'line_ids': [
                            (0, 0, {
                                'name': f"{picking.name} - {move.product_id.name}",
                                'account_id': acc_src,
                                'credit': abs(value),
                                'debit': 0.0,
                                'product_id': move.product_id.id,
                                'quantity': quantity,
                            }),
                            (0, 0, {
                                'name': f"{picking.name} - {move.product_id.name}",
                                'account_id': acc_dest,
                                'credit': 0.0,
                                'debit': abs(value),
                                'product_id': move.product_id.id,
                                'quantity': quantity,
                            }),
                        ],
                    }
                    try:
                        account_move = self.env['account.move'].sudo().create(move_vals)
                        account_move.action_post()
                        new_layer.account_move_id = account_move.id
                    except Exception as e:
                        # Log error but continue
                        _logger = self.env.logging.getLogger(__name__)
                        _logger.error(f"Failed to post account move for picking {picking.name}: {e}")
        message = _('Successfully re-processed valuation for %s picking(s).') % processed_count
        if skipped_count > 0:
            message += _(' %s non-Done picking(s) were skipped.') % skipped_count
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reprocess Valuation Result') if skipped_count == 0 else _('Partial Success' if processed_count > 0 else 'Error'),
                'message': message,
                'sticky': skipped_count > 0,
                'type': 'success' if skipped_count == 0 else ('warning' if processed_count > 0 else 'danger'),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
