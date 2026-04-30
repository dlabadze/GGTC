from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from io import BytesIO


class MobileDebt(models.Model):
    _name = 'mobile.debt'
    _description = 'Mobile Debt'
    _rec_name = 'comment'

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    comment = fields.Char(string='კომენტარი')
    mobile_details_ids = fields.One2many(
        'mobile.debt.detail',
        'mobile_debt_id',
        string='Mobile Details'
    )

    def action_generate_excel(self):
        """Generate an Excel file with one row per mobile_details_ids line."""
        self.ensure_one()

        if not self.mobile_details_ids:
            raise UserError(_("No mobile details to export."))

        try:
            from openpyxl import Workbook
        except ImportError:
            raise UserError(
                _("openpyxl library not installed. Please install it on the server: pip install openpyxl")
            )

        # Create workbook and sheet
        wb = Workbook()
        ws = wb.active
        ws.title = "Mobile Debt"

        # Header row
        headers = [
            "თანამშრომელი",
            "საიდენტიფიკაციო კოდი",
            "მობილურის ნომრები",
            "ატვირთული მობილურის ნომრები",
            "დავალიანება",
        ]
        ws.append(headers)

        # Data rows
        for line in self.mobile_details_ids:
            ws.append([
                line.employee_id.name or "",
                line.identification_id or "",
                line.private_phone or "",
                line.private_phone_from_excel or "",
                line.debt or 0.0,
            ])

        # Save to in‑memory buffer
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        data = base64.b64encode(buffer.read())
        filename = f"mobile_debt_{self.id}.xlsx"

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': data,
            'res_model': 'mobile.debt',
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

