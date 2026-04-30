from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Backfill comment and location_desk_id on account.move records
    created from stock moves, based on the picking's data."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    stock_moves = env['stock.move'].search([('picking_id', '!=', False)])

    for move in stock_moves:
        picking = move.picking_id
        account_moves = move.stock_valuation_layer_ids.mapped('account_move_id')

        if not account_moves:
            continue

        vals = {}
        comment = getattr(picking, 'comment', False)
        if comment:
            vals['comment'] = comment

        if (picking.location_dest_id and
                picking.location_dest_id.complete_name == 'Virtual Locations/ჩამოწერა'):
            vals['location_desk_id'] = picking.location_id.id

        if vals:
            account_moves.write(vals)
