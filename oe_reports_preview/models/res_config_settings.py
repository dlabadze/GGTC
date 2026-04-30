# -*- coding: utf-8 -*-
# This module is under copyright of 'OdooElevate'

from odoo import api, fields, models, _

class OEResConfigSettingsPreview(models.TransientModel):
    _inherit = 'res.config.settings'

    preview_pdf = fields.Boolean("PDF Report Preview", config_parameter='oe_reports_preview.preview_pdf' , default=False)

    @api.onchange('preview_pdf')
    def preview_pdf_changing(self):
        if self.preview_pdf:
            reports = self.env['ir.actions.report'].search([('report_type', '=', 'qweb-pdf')])
            reports.write({'report_type': 'qweb-html'})
        else:
            reports = self.env['ir.actions.report'].search([('report_type', '=', 'qweb-html')])
            reports.write({'report_type': 'qweb-pdf'})