# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'FMG Change Effective Date',
    'author': 'FMG Soft',
    'version': '18.0.1.0.18',
    'summary': 'Change Effective Date in Stock Picking',
    'license': 'OPL-1',
    'sequence': 1,
    'description': """Allows You Changing Effective Date of DO, RO, Internal and All Inventory Transfers""",
    'category': 'Inventory',
    'price':'40',
    'currency':'USD',
    'depends': [
        'account',
        'stock',
        'sale_management',
        'purchase',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/effective_date_change.xml',
        'views/effective_date_change_privilege.xml',
        'wizard/change_effective_wizard_views.xml',
    ],
    'images': [
        'static/description/assets/banner.png',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'pre_init_hook': 'pre_init_check',
}

