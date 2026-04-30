from odoo import models, fields, api
from datetime import datetime

class ChangeEffectiveWizard(models.TransientModel):
    _inherit = 'change.effective.wizard'

    def update_effective_date(self):
        """
        Complete replacement of fmg_effective_date_change logic.
        This version ensures sequences are cleared and cache is invalidated correctly.
        """
        for picking in self.env['stock.picking'].browse(self._context.get('active_ids', [])):
            # Determine the date
            selected_date = self.effective_date
            if not selected_date:
                from odoo.exceptions import ValidationError
                raise ValidationError('Date is not yet selected')
            
            target_date = selected_date.date() if isinstance(selected_date, datetime) else selected_date

            # 1. Update Picking and SVL dates
            picking.date_done = selected_date
            self.env.cr.execute("UPDATE stock_valuation_layer SET create_date = %s WHERE description LIKE %s", [selected_date, str(picking.name + "%")])
            
            # 2. Update Move dates
            for stock_move_line in self.env['stock.move.line'].search([('reference', 'ilike', str(picking.name + "%"))]):
                stock_move_line.date = selected_date
            for stock_move in self.env['stock.move'].search([('reference', 'ilike', str(picking.name + "%"))]):
                stock_move.date = selected_date

            # 3. Update Account Move dates and CLEAR sequences via SQL
            # We use NULL/0 to ensure Odoo treats them as needing new sequences
            self.env.cr.execute("""
                UPDATE account_move_line SET date = %s 
                WHERE move_id IN (SELECT id FROM account_move WHERE ref SIMILAR TO %s)
            """, [target_date, str(picking.name + "%")])
            
            self.env.cr.execute("""
                UPDATE account_move 
                SET date = %s, name = NULL, sequence_prefix = NULL, sequence_number = 0 
                WHERE ref SIMILAR TO %s
            """, [target_date, str(picking.name + "%")])

            # Invalidate cache for all affected moves
            affected_moves = self.env['account.move'].search([('ref', 'ilike', picking.name + '%')])
            affected_moves.invalidate_model(['date', 'name', 'sequence_prefix', 'sequence_number'])
            affected_moves.line_ids.invalidate_model(['date'])

            # 4. Handle complex logic (Outgoing/Incoming/AVCO/Currency)
            # We reuse the robust action_fix_accounting_dates method or inline the original logic
            # but with FIXES for the post cycle.
            
            # Since the original logic is very long, we call our unified fix method 
            # which we've designed to be robust.
            picking.action_fix_accounting_dates()

        return True
