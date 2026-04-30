import base64
from io import BytesIO

from odoo import fields, models, _
from odoo.exceptions import UserError

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None


class InventoryLinePriceUploadWizard(models.TransientModel):
    _name = "inventory.line.price.upload.wizard"
    _description = "Inventory Line Price Upload Wizard"

    request_id = fields.Many2one("inventory.request", required=True)
    excel_file = fields.Binary(string="Excel File", required=True)
    excel_filename = fields.Char(string="File Name")

    @staticmethod
    def _normalize_product_code(value):
        """Normalize excel/Odoo product codes for reliable string matching."""
        if pd is not None and pd.isna(value):
            return ""
        text_value = str(value).strip()
        if not text_value:
            return ""
        if text_value.endswith(".0"):
            integer_part = text_value[:-2]
            if integer_part.isdigit():
                return integer_part
        return text_value

    def action_confirm(self):
        self.ensure_one()
        request = self.request_id.sudo()

        if pd is None:
            raise UserError(_("Python package 'pandas' is not installed on the server."))

        if request.stage_id.name != "ბაზრის კვლევა და განფასება":
            raise UserError(
                _("ეს ოპერაცია ხელმისაწვდომია მხოლოდ ეტაპზე: ბაზრის კვლევა და განფასება.")
            )

        if not self.excel_file:
            raise UserError(_("გთხოვთ ატვირთოთ Excel ფაილი."))

        try:
            file_content = base64.b64decode(self.excel_file)
            df = pd.read_excel(
                BytesIO(file_content),
                usecols=[0, 1],
                header=None,
            )
        except Exception as err:
            raise UserError(_("Excel ფაილის წაკითხვა ვერ მოხერხდა: %s") % err) from err

        if df.empty:
            raise UserError(_("Excel ფაილი ცარიელია."))

        lines_by_code = {
            self._normalize_product_code(line.product_id.default_code): line
            for line in request.line_ids
            if line.product_id and line.product_id.default_code and line.x_studio_purchase
        }

        updated_count = 0
        for row_idx, row in df.iterrows():
            product_code = self._normalize_product_code(row.iloc[0])
            if not product_code:
                continue

            line = lines_by_code.get(product_code)
            if not line:
                continue

            price_value = row.iloc[1]
            if pd.isna(price_value):
                continue

            try:
                unit_price = float(price_value)
            except (TypeError, ValueError):
                continue

            line.sudo().write({"unit_price": unit_price})
            updated_count += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("განახლება დასრულდა"),
                "message": _("%s ჩანაწერი განახლდა.") % updated_count,
                "type": "success",
                "sticky": False,
            },
        }
