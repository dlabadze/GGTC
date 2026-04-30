from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def name_get(self):
        """For inventory.request lines, show only the product name."""
        if self.env.context.get("inventory_line_name_only"):
            return [(product.id, product.name or "") for product in self]
        return super().name_get()


