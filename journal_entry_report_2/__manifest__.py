{
    'name': 'Journal Entry Report 2',
    'version': '1.0',
    'summary': 'Custom report for journal entries with debit and credit pairing',
    'depends': ['base', 'account', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/country_code_action.xml',
        'views/journal_entry_report_wizard_view.xml',
        'views/country_code_import_views.xml',
    ],
    'installable': True,
}
