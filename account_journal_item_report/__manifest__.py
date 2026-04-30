{
    'name': 'Account Journal Item Report',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Journal Item Report Wizard with Starting/Ending Balance for Single Account',
    'author': 'Your Company',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_journal_item_report_wizard.xml',
        'wizard/trial_balance_wizard.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
} 