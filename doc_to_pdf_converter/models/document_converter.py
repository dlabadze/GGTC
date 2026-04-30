# -*- coding: utf-8 -*-
import base64
import tempfile
import os
import subprocess
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DocumentConverter(models.Model):
    _name = 'document.converter'
    _description = 'Document to PDF Converter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Document Name', required=True, default='New Document', tracking=True)
    docx_file = fields.Binary(string='DOCX File', attachment=True, tracking=True)
    docx_filename = fields.Char(string='DOCX Filename')
    pdf_file = fields.Binary(string='PDF File', attachment=True, readonly=True)
    pdf_filename = fields.Char(string='PDF Filename', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('converted', 'Converted'),
    ], string='Status', default='draft', readonly=True, tracking=True)
    conversion_date = fields.Datetime(string='Conversion Date', readonly=True)
    notes = fields.Text(string='Notes')

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
                # raise UserError(_('docx_path: %s') % docx_path) 
                with open(docx_path, 'wb') as f:
                    f.write(base64.b64decode(self.docx_file))
                
                # Try different conversion methods
                pdf_path = self._convert_with_libreoffice(docx_path, temp_dir)
                if not pdf_path:
                    pdf_path = self._convert_with_docx2pdf(docx_path, temp_dir)
                
                if not pdf_path:
                    raise UserError(_('PDF conversion failed. Please ensure LibreOffice or Microsoft Word is installed.'))
                
                # Read the generated PDF
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                # Update record
                pdf_filename = os.path.splitext(docx_filename)[0] + '.pdf'
                self.write({
                    'pdf_file': base64.b64encode(pdf_data),
                    'pdf_filename': pdf_filename,
                    'state': 'converted',
                    'conversion_date': fields.Datetime.now(),
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Document converted to PDF successfully!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
                
        except Exception as e:
            _logger.error(f'Error converting DOCX to PDF: {str(e)}')
            raise UserError(_('Error converting document: %s') % str(e))

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

    def action_reset_to_draft(self):
        """Reset document to draft state"""
        self.write({
            'state': 'draft',
            'pdf_file': False,
            'pdf_filename': False,
            'conversion_date': False,
        })

    def action_download_pdf(self):
        """Download the PDF file"""
        self.ensure_one()
        
        if not self.pdf_file:
            raise UserError(_('No PDF file available. Please convert the document first.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/document.converter/{self.id}/pdf_file/{self.pdf_filename or "document.pdf"}?download=true',
            'target': 'self',
        }