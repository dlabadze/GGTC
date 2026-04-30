# -*- coding: utf-8 -*-
{
    'name': 'Document to PDF Wizard',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Convert DOCX files to PDF using Wizard',
    'description': """
        Document to PDF Wizard
        ======================
        This module allows you to:
        * Upload DOCX files via wizard
        * Convert DOCX files to PDF with a single click
        * Download both DOCX and PDF files
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/doc_pdf_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

