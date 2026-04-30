{
    'name': 'Show Employee Pager Count',
    'depends': ['hr_payroll'],
    'data': [
        'views/inherit_pager_show.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'show_pager_count/static/src/js/force_pager.js',
        ],
    },
}