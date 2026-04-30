{
    'name': 'Moxsenebiti',
    'version': '1.0',
    'summary': 'Internal Moxsenebiti workflow',
    'category': 'HR',
    'depends': [
        'base',
        'mail',          # REQUIRED (mail.thread, activities)
        'hr',            # employee lines
        'fleet',         # car field
        #'hr_holidays',   # future leave logic (safe)
        'approvals',     # approval.request generation
        # 'hr_contract', # keep only if really needed
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/moxsenebiti_sequences.xml',   # 👈 REQUIRED
        'data/moxsenebiti_categories.xml',  # 👈 REQUIRED
        'views/moxsenebiti_view.xml',
        'wizard/moxsenebiti_send_to_order_view.xml',
        'wizard/moxsenebiti_prepare_order_view.xml',
        #'wizard/moxsenebiti_transport_dispatch_view.xml',
        'wizard/moxsenebiti_change_owner_view.xml',
        'wizard/moxsenebiti_reinitiate_view.xml',
        'wizard/moxsenebiti_add_approver_view.xml',
    ],
    'installable': True,
    'application': True,
}
