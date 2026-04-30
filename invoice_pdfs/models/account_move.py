from odoo import models, api
import base64
import io
import zipfile
import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_download_separate_pdfs(self):
        def get_custom_filename(inv):
            customer_name = inv.partner_id.name or "Unknown_Customer"
            safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')[:50]
            return f"{safe_name}_საურავი გგს.pdf"

        if len(self) == 1:
            report = self.env.ref('invoice_pdfs.action_report_invoice_transport_report')
            filename = get_custom_filename(self)
            return report.report_action(self, config=False).update({
                'report_file': filename,
            })

        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as zip_file:
            for invoice in self:
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                    'invoice_pdfs.report_invoice_custom',
                    invoice.ids
                )

                customer_name = invoice.partner_id.name or "Unknown_Customer"
                safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_name = safe_name.replace(' ', '_')[:50]
                filename = f"{safe_name}_საურავი გგს.pdf"
                zip_file.writestr(filename, pdf_content)

        zip_data = base64.b64encode(stream.getvalue())

        attachment = self.env['ir.attachment'].create({
            'name': 'Invoices.zip',
            'type': 'binary',
            'datas': zip_data,
            'mimetype': 'application/zip',
            'res_model': 'account.move',
            'res_id': self[0].id if self else False,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_separate_pdfs_transport(self):
        def get_custom_filename(inv):
            customer_name = inv.partner_id.name or "Unknown_Customer"
            safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')[:50]
            return f"{safe_name}_საურავი_ტრანსპორტირება.pdf"

        if len(self) == 1:
            report = self.env.ref('invoice_pdfs.action_report_invoice_transport_report')
            filename = get_custom_filename(self)
            return report.report_action(self, config=False).update({
                'report_file': filename,
            })
        
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as zip_file:
            for invoice in self:
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                    'invoice_pdfs.report_invoice_transport_custom',
                    invoice.ids
                )

                customer_name = invoice.partner_id.name or "Unknown_Customer"
                safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_name = safe_name.replace(' ', '_')[:50]

                filename = f"{safe_name}_საურავი ტრანსპორტირება.pdf"
                zip_file.writestr(filename, pdf_content)

        zip_data = base64.b64encode(stream.getvalue())

        attachment = self.env['ir.attachment'].create({
            'name': 'Invoices.zip',
            'type': 'binary',
            'datas': zip_data,
            'mimetype': 'application/zip',
            'res_model': 'account.move',
            'res_id': self[0].id if self else False,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_separate_pdfs_other(self):
        if len(self) == 1:
            return self.env.ref('invoice_pdfs.action_report_invoice_other_report').report_action(self)

        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as zip_file:
            for invoice in self:
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                    'invoice_pdfs.report_invoice_other_custom',
                    invoice.ids
                )

                customer_name = invoice.partner_id.name or "Unknown_Customer"
                safe_name = "".join(c for c in customer_name if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_name = safe_name.replace(' ', '_')[:50]

                filename = f"{safe_name}_Invoice.pdf"
                zip_file.writestr(filename, pdf_content)

        zip_data = base64.b64encode(stream.getvalue())

        attachment = self.env['ir.attachment'].create({
            'name': 'Invoices.zip',
            'type': 'binary',
            'datas': zip_data,
            'mimetype': 'application/zip',
            'res_model': 'account.move',
            'res_id': self[0].id if self else False,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }