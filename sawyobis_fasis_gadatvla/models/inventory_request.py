from odoo import _, models


class InventoryRequest(models.Model):
    _inherit = "inventory.request"

    def action_sawyobis_fasis_gadatvla(self):
        for request in self:
            lines_to_update = request.line_ids.filtered(
                lambda line: not line.x_studio_purchase and line.product_id
            )
            for line in lines_to_update:
                line.unit_price = line.product_id.standard_price

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("შესრულდა"),
                "message": _("საწყობის ფასები განახლდა"),
                "type": "success",
                "sticky": False,
            },
        }
