from odoo import api, fields, models



class InventoryLine(models.Model):
    _inherit = "inventory.line"

    unit_price_xelsh = fields.Float(
        string="ერთეულის ფასი ხელშ.",
        compute="_compute_xelsh_fields",
        store=True,
        readonly=False,
    )
    amount_xelsh = fields.Float(
        string="ჯამური ფასი ხელშ.",
        compute="_compute_xelsh_fields",
        store=True,
        readonly=False,
    )

    @api.depends("request_id.stage_id")
    def _compute_xelsh_fields(self):
        for line in self:
            stage = line.request_id.stage_id
            if stage and stage.name == "დადასტურებული":
                line.unit_price_xelsh = line.unit_price
                line.amount_xelsh = line.amount
            else:
                line.unit_price_xelsh = 0.0
                line.amount_xelsh = 0.0
