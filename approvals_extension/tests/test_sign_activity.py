from odoo import fields
from odoo.tests.common import TransactionCase

class TestApprovalSignActivity(TransactionCase):

    def setUp(self):
        super(TestApprovalSignActivity, self).setUp()
        self.approval_model = self.env['approval.request']
        self.activity_model = self.env['mail.activity']
        self.user = self.env.user
        
        # Create an approval request
        self.request = self.approval_model.create({
            'name': 'Test Request',
            'request_owner_id': self.user.id,
            'category_id': self.env.ref('approvals.approval_category_data_business_trip').id,
        })

    def test_mark_activity_done(self):
        # Create an activity for the user
        activity = self.activity_model.create({
            'res_model': 'approval.request',
            'res_id': self.request.id,
            'user_id': self.user.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': 'Test Activity',
        })
        
        # Verify activity is active
        self.assertTrue(activity.active)
        self.assertFalse(activity.date_done)
        
        # Call the helper method directly
        self.request._mark_activity_done()
        
        # Verify activity is done (archived/marked done depending on Odoo version, usually active=False for done activities in search default, strictly speaking it sets state='done' or unlink)
        # In Odoo, action_done() usually unlinks the activity and creates a message.
        # So we check if it still exists.
        
        activity_exists = self.activity_model.search([('id', '=', activity.id)])
        self.assertFalse(activity_exists, "Activity should be removed (marked done) after calling _mark_activity_done")

