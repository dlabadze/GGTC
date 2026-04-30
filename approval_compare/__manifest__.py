{
    'name': 'ბუღალტრული შედარება',
    'version': '1.1',
    'summary': 'სერვერ-აქშენის გამოთვლილი თანხების შედარება ფაქტიურ ბუღალტრულ ჩანაწერებთან',
    'category': 'HR',
    'depends': [
        'approvals',
        'account',
        'hr_approval_mod',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/mission_accounting_comparison.xml',
    ],
    'installable': True,
    'application': False,
}
