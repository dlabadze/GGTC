from odoo import api, fields, models, _


class InventoryRequest(models.Model):
    _inherit = "inventory.request"

    can_upload_excel_prices = fields.Boolean(
        compute="_compute_can_upload_excel_prices",
        string="Can Upload Excel Prices",
    )

    @api.depends("stage_id")
    def _compute_can_upload_excel_prices(self):
        for rec in self:
            rec.can_upload_excel_prices = (
                rec.stage_id.name == "ბაზრის კვლევა და განფასება"
            )

    def action_open_inventory_line_price_upload_wizard(self):
        self.ensure_one()
        return {
            "name": _("ექსელის ატვირთვა"),
            "type": "ir.actions.act_window",
            "res_model": "inventory.line.price.upload.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_id": self.id,
            },
        }
