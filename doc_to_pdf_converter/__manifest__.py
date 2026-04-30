# -*- coding: utf-8 -*-
{
    'name': 'Document to PDF Converter',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Convert DOCX files to PDF',
    'description': """
        Document to PDF Converter
        =========================
        This module allows you to:
        * Upload DOCX files
        * Convert DOCX files to PDF with a single click
        * Store both DOCX and PDF files in the system
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/document_converter_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

