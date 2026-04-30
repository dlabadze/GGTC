from odoo import models, fields, api
from odoo.exceptions import UserError


class StockMoveLineDateFix(models.TransientModel):
    _name = 'stock.move.line.date.fix'
    _description = 'Wizard to Fix Stock Date'

    new_date = fields.Datetime(string="New Date", required=True, default=fields.Datetime.now)

    def action_update_date(self):
        active_ids = self.env.context.get('active_ids', [])
        lines = self.env['stock.move.line'].browse(active_ids)

        processed_moves = set()
        processed_pickings = set()
        processed_account_moves = set()

        for line in lines:
            line.write({'date': self.new_date})

            move = line.move_id
            if not move:
                continue

            if move.id not in processed_moves:
                move.write({'date': self.new_date})
                if move.stock_valuation_layer_ids:
                    self.env.cr.execute("""
                        UPDATE stock_valuation_layer
                        SET create_date = %s
                        WHERE stock_move_id = %s
                    """, (self.new_date, move.id))

                processed_moves.add(move.id)

            picking = move.picking_id
            if picking and picking.id not in processed_pickings:
                if picking.state != 'cancel':
                    self.env.cr.execute("""
                        UPDATE stock_picking 
                        SET date_done = %s, scheduled_date = %s 
                        WHERE id = %s
                    """, (self.new_date, self.new_date, picking.id))

                    picking.invalidate_recordset(['date_done', 'scheduled_date'])

                processed_pickings.add(picking.id)

            if move.account_move_ids:
                for journal_entry in move.account_move_ids:
                    if journal_entry.id in processed_account_moves:
                        continue

                    if journal_entry.state == 'cancel':
                        continue

                    was_posted = (journal_entry.state == 'posted')

                    if was_posted:
                        journal_entry.button_draft()

                    journal_entry.write({'date': self.new_date})

                    if was_posted:
                        journal_entry.action_post()

                    processed_account_moves.add(journal_entry.id)

        return {'type': 'ir.actions.act_window_close'}