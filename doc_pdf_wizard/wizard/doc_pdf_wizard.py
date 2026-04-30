# -*- coding: utf-8 -*-
import base64
import tempfile
import os
import subprocess
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
try:
    from docxtpl import DocxTemplate
except ImportError:
    DocxTemplate = None

_logger = logging.getLogger(__name__)


class DocPdfWizard(models.TransientModel):
    _name = 'doc.pdf.wizard'
    _description = 'Document to PDF Conversion Wizard'

    name = fields.Char(string='Document Name', required=True, default='New Document')
    docx_file = fields.Binary(string='DOCX File', attachment=True, required=True)
    docx_filename = fields.Char(string='DOCX Filename')
    pdf_file = fields.Binary(string='PDF File', attachment=True, readonly=True)
    pdf_filename = fields.Char(string='PDF Filename', readonly=True)
    state = fields.Selection([
        ('upload', 'Upload'),
        ('converted', 'Converted'),
    ], string='Status', default='upload', readonly=True)
    conversion_date = fields.Datetime(string='Conversion Date', readonly=True)
    
    # Context fields to track the source record
    source_model = fields.Char(string='Source Model')
    source_res_id = fields.Integer(string='Source Record ID')

    @api.model
    def default_get(self, fields_list):
        """Get default values from context"""
        res = super(DocPdfWizard, self).default_get(fields_list)
        
        # Get source model and record from context
        if self.env.context.get('active_model'):
            res['source_model'] = self.env.context.get('active_model')
        if self.env.context.get('active_id'):
            res['source_res_id'] = self.env.context.get('active_id')
        
        return res

    @api.onchange('docx_filename')
    def _onchange_docx_filename(self):
        """Auto-fill name from filename"""
        if self.docx_filename and self.name == 'New Document':
            name_without_ext = os.path.splitext(self.docx_filename)[0]
            self.name = name_without_ext

    def action_convert_to_pdf(self):
        """Convert DOCX file to PDF"""
        self.ensure_one()
        
        if not self.docx_file:
            raise UserError(_('Please upload a DOCX file first.'))
        
        try:
            # Create temporary directory for conversion
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save DOCX file
                docx_filename = self.docx_filename or 'document.docx'
                docx_path = os.path.join(temp_dir, docx_filename)
                
                with open(docx_path, 'wb') as f:
                    f.write(base64.b64decode(self.docx_file))

                # Render the DOCX with record data if available
                try:
                    self._render_docx_template_if_needed(docx_path)
                except Exception as render_err:
                    _logger.error('Error rendering DOCX template before conversion: %s', render_err)
                    raise UserError(_('Failed to render the DOCX template: %s') % render_err)
                
                # Try different conversion methods
                pdf_path = self._convert_with_libreoffice(docx_path, temp_dir)
                if not pdf_path:
                    pdf_path = self._convert_with_docx2pdf(docx_path, temp_dir)
                
                if not pdf_path:
                    raise UserError(_('PDF conversion failed. Please ensure LibreOffice or Microsoft Word is installed.'))
                
                # Read the generated PDF
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                # Update wizard
                pdf_filename = os.path.splitext(docx_filename)[0] + '.pdf'
                pdf_base64 = base64.b64encode(pdf_data)
                
                self.write({
                    'pdf_file': pdf_base64,
                    'pdf_filename': pdf_filename,
                    'state': 'converted',
                    'conversion_date': fields.Datetime.now(),
                })
                
                # Attach PDF to source record if context provides model and id
                if self.source_model and self.source_res_id:
                    self._attach_pdf_to_record(pdf_base64, pdf_filename)
                    message = _('PDF converted and attached to record successfully!')
                else:
                    message = _('Document converted to PDF successfully!')
                
                # Show notification and close window
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': message,
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
                
        except Exception as e:
            _logger.error(f'Error converting DOCX to PDF: {str(e)}')
            raise UserError(_('Error converting document: %s') % str(e))

    def _render_docx_template_if_needed(self, docx_path):
        """Render DOCX template with record data so Jinja placeholders (including images) are replaced."""
        if not (self.source_model and self.source_res_id):
            return
        record = self.env[self.source_model].browse(self.source_res_id)
        if not record:
            return
        if DocxTemplate is None:
            raise UserError(_('The library "docxtpl" is required to render DOCX templates.'))

        doc_template = DocxTemplate(docx_path)
        report_model = self.env['ir.actions.report']
        context = report_model._get_rendering_context_docx(doc_template)
        context.update({
            'docs': record,
            'doc_ids': record.ids,
            'doc_model': record._name,
            'objects': record,
            'object': record,
            'env': self.env,
            'data': self.env.context.get('data', {}),
        })

        doc_template.render(context, autoescape=False)
        doc_template.save(docx_path)

    def _convert_with_libreoffice(self, docx_path, output_dir):
        """Convert using LibreOffice headless mode"""
        try:
            # Try common LibreOffice paths
            libreoffice_paths = [
                'libreoffice',
                'soffice',
                '/usr/bin/libreoffice',
                '/usr/bin/soffice',
                'C:\\Program Files\\LibreOffice\\program\\soffice.exe',
                'C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe',
            ]
            
            libreoffice_cmd = None
            for path in libreoffice_paths:
                try:
                    result = subprocess.run(
                        [path, '--version'],
                        capture_output=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        libreoffice_cmd = path
                        break
                except:
                    continue
            
            if not libreoffice_cmd:
                _logger.warning('LibreOffice not found')
                return None
            
            # Convert to PDF
            cmd = [
                libreoffice_cmd,
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                docx_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
                text=True
            )
            
            if result.returncode == 0:
                # Find the generated PDF
                pdf_filename = os.path.splitext(os.path.basename(docx_path))[0] + '.pdf'
                pdf_path = os.path.join(output_dir, pdf_filename)
                
                if os.path.exists(pdf_path):
                    _logger.info('PDF converted successfully with LibreOffice')
                    return pdf_path
            else:
                _logger.warning(f'LibreOffice conversion failed: {result.stderr}')
                
        except Exception as e:
            _logger.warning(f'LibreOffice conversion error: {str(e)}')
        
        return None

    def _convert_with_docx2pdf(self, docx_path, output_dir):
        """Convert using docx2pdf library (requires Microsoft Word on Windows)"""
        try:
            import docx2pdf
            
            pdf_filename = os.path.splitext(os.path.basename(docx_path))[0] + '.pdf'
            pdf_path = os.path.join(output_dir, pdf_filename)
            
            docx2pdf.convert(docx_path, pdf_path)
            
            if os.path.exists(pdf_path):
                _logger.info('PDF converted successfully with docx2pdf')
                return pdf_path
                
        except ImportError:
            _logger.warning('docx2pdf library not installed')
        except Exception as e:
            _logger.warning(f'docx2pdf conversion error: {str(e)}')
        
        return None

    def _attach_pdf_to_record(self, pdf_data, pdf_filename):
        """Attach the converted PDF to the source record"""
        self.ensure_one()
        
        if not self.source_model or not self.source_res_id:
            return
        
        try:
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': pdf_filename,
                'type': 'binary',
                'datas': pdf_data,
                'res_model': self.source_model,
                'res_id': self.source_res_id,
                'mimetype': 'application/pdf',
            })
            
            _logger.info(f'PDF attached to {self.source_model}({self.source_res_id}): {pdf_filename}')
            
        except Exception as e:
            _logger.error(f'Error attaching PDF to record: {str(e)}')


