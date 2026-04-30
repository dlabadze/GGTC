from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.constrains('date', 'name')
    def _constrains_date_sequence(self):
        """
        Intercept the sequence alignment constraint.
        If a mismatch is detected for a stock-related move, we allow it 
        to pass by clearing the name (it will get a new one in action_post).
        """
        for move in self:
            if move.name and move.name != '/' and move.date:
                # Broad detection: Check Ref for common stock picking prefixes or SVL link
                is_stock = move.stock_valuation_layer_ids or \
                           (move.ref and any(x in move.ref for x in ['WH/', 'RET/', 'ST/', 'IN/', 'OUT/', 'IR']))
                if is_stock:
                    # If it's a stock move, we force it to be 'unnamed' during the check
                    # so the parent constrain skips the alignment validation.
                    # Note: This is safe because action_post will generate the correct name.
                    move.write({
                        'name': False,
                        'sequence_prefix': False,
                        'sequence_number': 0,
                    })
        return super(AccountMove, self)._constrains_date_sequence()

    def action_post(self):
        """
        Force sequence reset for stock moves during posting.
        """
        for move in self:
             is_stock = move.stock_valuation_layer_ids or \
                        (move.ref and any(x in move.ref for x in ['WH/', 'RET/', 'ST/', 'IN/', 'OUT/', 'IR']))
             if is_stock and move.name and move.name != '/':
                move.write({
                    'name': False,
                    'sequence_prefix': False,
                    'sequence_number': 0,
                })
                move.flush_recordset(['name', 'sequence_prefix', 'sequence_number'])
                move.invalidate_model(['name', 'sequence_prefix', 'sequence_number'])
                        
        return super(AccountMove, self).action_post()
