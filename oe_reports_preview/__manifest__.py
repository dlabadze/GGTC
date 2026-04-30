# -*- coding: utf-8 -*-
# This module is under copyright of 'OdooElevate'
{
    'name': 'PDF Reports Preview',
    'version': '18.0.0.1.1',
    'website': 'https://odooelevate.odoo.com/',
    'author': 'Sheikh Muhammad Saad, OdooElevate',
    'summary': 'Allows quick preview of PDF reports before downloading.',
    'description': """
        This module provides a convenient way to preview PDF reports before downloading directly within Odoo.
        By ticking a checkbox in the General Settings, all PDF reports will be converted to Preview Mode,
        enabling faster debugging and review without needing to download PDFs.
    """,
    'category': 'Extra Tools',
    'depends': [
        'base', 'base_setup'
    ],
    'data': [
        'views/res_config_settings.xml',
    ],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'AGPL-3',
}
