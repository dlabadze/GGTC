from odoo import api, fields, models



class InventoryLine(models.Model):
    _inherit = "inventory.line"

    unit_price_xelsh = fields.Float(
        string="ერთეულის ფასი ხელშ.",
    )
    amount_xelsh = fields.Float(
        string="ჯამური ფასი ხელშ.",
        compute="_compute_xelsh_fields",
        store=True,
        readonly=False,
    )

    @api.depends("quantity", "unit_price_xelsh")
    def _compute_xelsh_fields(self):
        for line in self:
            line.amount_xelsh = line.quantity * line.unit_price_xelsh

    def _create_purchase_agreement_direct(self, lines, vendor, purchase_method=None):
        """Override price/amount sources for direct agreement creation."""
        agreement = super()._create_purchase_agreement_direct(lines, vendor, purchase_method=purchase_method)

        line_model = self.env["purchase.requisition.line"]
        has_total_amount = "total_amount" in line_model._fields

        for agreement_line in agreement.line_ids:
            inventory_line = agreement_line.inventory_line_ids[:1]
            if not inventory_line:
                continue

            price = inventory_line.unit_price_xelsh
            vals = {"price_unit": price}

            if has_total_amount:
                vals["total_amount"] = agreement_line.product_qty * price

            agreement_line.write(vals)

        if "requested_amount" in agreement._fields:
            agreement.write({"requested_amount": sum(lines.mapped("amount_xelsh"))})

        return agreement
