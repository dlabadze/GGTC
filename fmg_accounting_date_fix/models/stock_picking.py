from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_fix_accounting_dates(self):
        """
        More robust logic to fix accounting dates (account.move.date) 
        for associated journal entries of a picking.
        """
        for picking in self:
            # Determine the target date from fmg_effective_date_change's field or standard date_done
            selected_date = picking.date_of_transfer or picking.date_done
            if not selected_date:
                raise UserError(_("Please set an Effective Date or Date Done on the picking %s first.") % picking.name)
            
            target_date = selected_date.date() if isinstance(selected_date, (datetime, fields.Datetime)) else selected_date

            # 1. Update dates on the picking and its moves for consistency
            self.env.cr.execute("UPDATE stock_picking SET date_done = %s WHERE id = %s", (selected_date, picking.id))
            self.env.cr.execute("UPDATE stock_move SET date = %s WHERE picking_id = %s", (selected_date, picking.id))
            self.env.cr.execute("UPDATE stock_move_line SET date = %s WHERE picking_id = %s", (selected_date, picking.id))
            
            # 2. Update stock valuation layers
            svls = self.env['stock.valuation.layer'].search([
                '|',
                ('stock_move_id.picking_id', '=', picking.id),
                ('reference', 'ilike', picking.name + '%')
            ])
            if svls:
                self.env.cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE id IN %s", (selected_date, tuple(svls.ids)))

            # 3. Handle Account Moves (Journal Entries)
            # Find moves by SVL link, by Ref, or by Name (if name was set to picking name)
            moves = svls.mapped('account_move_id')
            
            extra_moves = self.env['account.move'].search([
                '|', ('ref', 'ilike', picking.name + '%'), ('name', 'ilike', picking.name + '%'),
                ('id', 'not in', moves.ids)
            ])
            moves |= extra_moves

            for move in moves:
                # Store original state
                original_state = move.state
                
                # If posted, we must set to draft to change the date and allow sequence recalculation
                if move.state == 'posted':
                    move.button_draft()
                
                # Update date and reset name to force sequence regeneration
                # Using NULL (False) instead of '/' is often more reliable in Odoo 17/18
                # to trigger a fresh sequence generation.
                self.env.cr.execute("""
                    UPDATE account_move 
                    SET date = %s, 
                        name = NULL, 
                        sequence_prefix = NULL,
                        sequence_number = 0
                    WHERE id = %s
                """, (target_date, move.id))
                self.env.cr.execute("UPDATE account_move_line SET date = %s WHERE move_id = %s", (target_date, move.id))
                
                # Clear cache so ORM sees the changes
                move.invalidate_model(['date', 'name', 'sequence_prefix', 'sequence_number'])
                move.line_ids.invalidate_model(['date'])

                # Re-post if it was originally posted
                if original_state == 'posted':
                    try:
                        move.action_post()
                        # Handle the custom field mention if it exists
                        if hasattr(move, 'made_sequence_gap'):
                            move.made_sequence_gap = False
                    except Exception as e:
                        # Log or notify user if re-posting fails
                        pass
            
            # Clear picking cache
            picking.invalidate_model(['date_done'])
            picking.move_ids.invalidate_model(['date'])
            picking.move_line_ids.invalidate_model(['date'])
            
        return True

    def button_validate(self):
        """
        Extend the validation process to automatically fix accounting dates 
        if an Effective Date (date_of_transfer) is set.
        """
        res = super(StockPicking, self).button_validate()
        
        for picking in self:
            if picking.date_of_transfer:
                picking.action_fix_accounting_dates()
                
        return res
