from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_declaration_number = fields.Char(
        string='დეკლარაციის ნომერი'
    )

    x_request_number_manual = fields.Char(
        string='მოთხოვნის ნომერი (ხელით)'
    )

    x_contract_number_manual = fields.Char(
        string='ხელშეკრულების ნომერი (ხელით)'
    )

    x_is_odorant_picking = fields.Boolean(
        compute='_compute_x_is_odorant_picking',
        store=False
    )

    @api.depends('picking_type_id')
    def _compute_x_is_odorant_picking(self):
        for picking in self:
            picking.x_is_odorant_picking = (
                picking.picking_type_id.name == 'ოდორანტის ჩამოწერა'
                if picking.picking_type_id else False
            )
