{
    'name': 'SMS Service',
    'version': '1.0',
    'category': 'Communication',
    'summary': 'Send SMS messages via Magti SMS service',
    'description': """
        This module provides functionality to send SMS messages via the Magti SMS service.
        Features:
        - Send SMS messages to phone numbers
        - Configure SMS service credentials
        - Track SMS sending history
        - Integration with Odoo messaging system
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/sms_config_views.xml',
        'views/sms_history_views.xml',
        'views/sms_menu_views.xml',
        'wizard/send_sms_wizard_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
} 