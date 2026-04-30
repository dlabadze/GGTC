from odoo import models, fields, api
import base64


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        result = super(IrActionsReport, self)._render_qweb_pdf(report_ref, res_ids, data)
        self._save_approval_report(report_ref, res_ids, result[0], 'pdf')
        return result

    def _render_docx(self, report_ref, res_ids=None, data=None):
        result = super(IrActionsReport, self)._render_docx(report_ref, res_ids, data)

        if isinstance(result, tuple):
            docx_content = result[0]
        else:
            docx_content = result

        self._save_approval_report(report_ref, res_ids, docx_content, 'docx')
        return result

    def _save_approval_report(self, report_ref, res_ids, content, extension):
        if not res_ids or not content:
            return

        report = self._get_report(report_ref)
        if report.model == 'approval.request':
            docids = [res_ids] if isinstance(res_ids, int) else res_ids
            records = self.env['approval.request'].sudo().browse(docids)

            for record in records.exists():
                if not record.x_studio_file:
                    filename = f"ბრძანება_{record.name or 'report'}.{extension}".replace('/', '_')

                    if isinstance(content, bytes):
                        record.write({
                            'x_studio_file': base64.b64encode(content),
                            'x_studio_file_filename': filename
                        })
        elif report.model == 'moxsenebiti':
            docids = [res_ids] if isinstance(res_ids, int) else res_ids
            records = self.env['moxsenebiti'].sudo().browse(docids)

            for record in records.exists():
                if not record.word_file:
                    filename = f"მოხსენება {record.name or 'report'}.{extension}".replace('/', '_')

                    if isinstance(content, bytes):
                        record.write({
                            'word_file': base64.b64encode(content),
                            'word_filename': filename
                        })
