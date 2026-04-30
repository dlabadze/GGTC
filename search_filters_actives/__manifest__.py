{
    'name': 'Account Asset Extended Search Filters',
    'version': '1.0',
    'summary': 'Adds Studio and standard field filters to account.asset search view',
    'category': 'Accounting',
    'depends': [
        'base',
        'account_asset',
        'web_studio',
    ],
    'data': [
        'views/search_filters.xml'
    ],
    'installable': True,
}