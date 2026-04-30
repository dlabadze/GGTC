from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        vals = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        picking = self.picking_id
        if picking:
            if picking.comment:
                vals['comment'] = picking.comment
            if picking.location_dest_id:
                if picking.location_dest_id.complete_name == 'Virtual Locations/ჩამოწერა':
                    vals['location_desk_id'] = picking.location_id.id
        return vals

    number = fields.Integer(string='Number', readonly=True)

    @api.onchange('picking_id', 'sequence')
    def _onchange_picking_id_number(self):
        """Set number based on position in move_ids_without_package (1, 2, 3, 4...) when picking_id or sequence changes"""
        self._assign_sequential_numbers()

    def _assign_sequential_numbers(self):
        """Assign sequential numbers (1, 2, 3...) to all moves in the picking"""
        if not self.picking_id:
            self.number = 0
            return

        all_picking_moves = self.picking_id.move_ids_without_package
        if self not in all_picking_moves:
            all_picking_moves = all_picking_moves | self

        moves = all_picking_moves.sorted(lambda m: (m.sequence or 0, m.id or 0))

        for index, move in enumerate(moves, start=1):
            move.number = index

    def write(self, vals):
        """Override write to reassign sequential numbers when moves are updated"""
        result = super(StockMove, self).write(vals)
        if 'picking_id' in vals or 'sequence' in vals:
            for move in self:
                if move.picking_id:
                    all_moves = move.picking_id.move_ids_without_package.sorted(lambda m: (m.sequence or 0, m.id or 0))
                    for index, picking_move in enumerate(all_moves, start=1):
                        picking_move.number = index
        return result

    def unlink(self):
        """Override unlink to renumber remaining moves after deletion"""
        pickings_to_renumber = self.mapped('picking_id').filtered('id')

        result = super(StockMove, self).unlink()

        for picking in pickings_to_renumber:
            if picking.exists():
                all_moves = picking.move_ids_without_package.sorted(lambda m: (m.sequence or 0, m.id or 0))
                for index, move in enumerate(all_moves, start=1):
                    move.number = index

        return result

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to assign sequential numbers when moves are created"""
        moves = super(StockMove, self).create(vals_list)
        for picking in moves.mapped('picking_id'):
            if picking:
                all_moves = picking.move_ids_without_package.sorted(lambda m: (m.sequence or 0, m.id or 0))
                for index, move in enumerate(all_moves, start=1):
                    move.number = index
        return moves
