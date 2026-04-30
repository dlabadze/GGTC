{
    'name': 'approval_modification',
    'version': '1.2',
    'summary': 'approval modification',
    'category': 'HR',
    'depends': [
        'base',
        'approvals',      # <– this is the correct module
        'hr',
        'hr_contract',
        'hr_holidays',   # ✅ REQUIRED (hr.leave logic)
        'account',       # Added because we inherit account.move
        #'approvals.approver',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_approval_mod_view.xml',
    ],
    #'sequence': 999,
    'installable': True,
    'application': False,
}
