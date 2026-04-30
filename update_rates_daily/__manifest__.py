{
    'name': 'Update Rates Daily',
    'version': '1.0',
    'summary': 'updates rates every day',
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cron_job.xml',
    ],
    'installable': True,
}