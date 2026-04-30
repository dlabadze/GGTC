{
    'name': 'September Excel Upload',
    'version': '1.0',
    'category': 'Custom',
    'summary': 'Upload Excel file to fill September request lines',
    'description': """
        This module allows uploading an Excel file to automatically create/update 
        lines in September Request form.
    """,
    'author': 'Giorgi Olqiashvili',
    'depends': ['base', 'web_studio', 'product', 'september_requests'],
    'data': [
        'security/ir.model.access.csv',
        'views/september_excel_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
