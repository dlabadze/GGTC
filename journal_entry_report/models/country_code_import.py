import io
import base64
import pandas as pd
from odoo.exceptions import UserError
from odoo import models, fields, api, _

class CountryCodeImport(models.Model):
    _name = 'country.code.import'
    _description = 'Country Code Excel Import'

    file = fields.Binary('Excel File', required=True)
    filename = fields.Char('File Name')

    def action_import_country_codes(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_("Please upload an Excel file."))

        try:
            file_data = io.BytesIO(base64.b64decode(self.file))
            df = pd.read_excel(file_data, dtype=str)
        except Exception as e:
            raise UserError(_("Failed to read Excel file: %s") % str(e))

        for _, row in df.iterrows():
            country = str(row.get('ქვეყნის დასახელება', '')).strip()
            code_raw = row.get('ID', '').strip()

            code = code_raw.zfill(3) if code_raw.isdigit() else code_raw

            if not country or not code:
                continue

            self.env['res.country.code.map'].sudo().update_or_create_country_code(country, code)

        return {'type': 'ir.actions.act_window_close'}
