from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import io
import openpyxl

class SeptemberExcelWizard(models.TransientModel):
    _name = 'september.excel.wizard'
    _description = 'Upload Excel to Fill September Lines'

    excel_file = fields.Binary(string='Excel File', required=True)
    file_name = fields.Char(string='File Name')
    request_id = fields.Many2one('september.request', string='Request')

    def action_upload_excel(self):
        if not self.excel_file:
            raise UserError("გთხოვთ ატვირთოთ Excel ფაილი!")

        if not self.request_id:
            raise UserError("მშობელი ჩანაწერი ვერ მოიძებნა!")

        file_data = base64.b64decode(self.excel_file)
        workbook = openpyxl.load_workbook(io.BytesIO(file_data))
        sheet = workbook.active

        missing_codes = []

        for row in sheet.iter_rows(min_row=2, values_only=True):
            code = row[0]
            qty = row[3]
            if not code:
                continue
            product = self.env['product.product'].search([('default_code', '=', code)], limit=1)
            if not product:
                missing_codes.append(code)

            # Check if this code already exists in the request lines
            existing_line = self.request_id.line_ids.filtered(
                lambda l: l.x_studio_related_field_1pq_1j2ffqufh == code
            )
            if existing_line:
                # Optional: you could update qty instead of creating a duplicate
                existing_line.quantity += qty or 0
                continue

            self.env['september.line'].create({
                'product_id': product.id if product else False,
                'x_studio_related_field_1pq_1j2ffqufh': code,
                'quantity': qty or 0,
                'request_id': self.request_id.id,
                'name': product.name if product else code,  # mandatory field filled
            })

        msg = "Excel ფაილი წარმატებით აიტვირთა!"
        if missing_codes:
            msg += "\nმაგრამ შემდეგი კოდები ვერ მოიძებნა პროდუქციის ბაზაში: " + ", ".join(missing_codes)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'წარმატება',
                'message': msg,
                'type': 'success',
            }
        }


class SeptemberRequest(models.Model):
    _inherit = 'september.request'

    def action_open_excel_wizard(self):
        return {
            'name': 'Upload Excel',
            'type': 'ir.actions.act_window',
            'res_model': 'september.excel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }
