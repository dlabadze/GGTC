# from odoo import models, fields, api
# from datetime import datetime
# from odoo.exceptions import UserError

# import logging
# _logger = logging.getLogger(__name__)

# class InventoryRequest(models.Model):
#     _inherit = 'inventory.request'

#     approver_users_ids = fields.One2many('inventory.request.approver.users', 'inventory_request_id', string='Approver Users')

#     def _handle_stage_activities(self, old_stage_name, new_stage_name):
#         """
#         Handle activity creation and completion based on stage changes
#         """
#         _logger.info(f"===============_handle_stage_activities===============")
#         _logger.info(f"old_stage_name: {old_stage_name} new_stage_name: {new_stage_name}")
        
#         # Define stage-to-field mapping
#         stage_field_mapping = {
#             "ადგ. საწყობი": 'x_studio_many2many_field_9d8_1jcbd2e76',
#             "ზემდგომი": 'x_studio_zemdgomi_1',
#             "ფილიალის უფროსი": 'x_studio_filial_ufros_1',
#             "დეპ. ხელმძღვანელი": 'x_studio_tech_dep_1',
#             "ხელმძღვანელი": 'x_studio_tech_director_1',
#             "სასაწყობე მეურ. სამმ.": 'x_studio_whs_sam_1',
#             "ლოგისტიკის დეპარტამენტი": 'x_studio_logist_dep_1',
#             "ლოგისტიკის დირექტორი": 'x_studio_logist_dir_1',
#             "შესყ. დეპ. უფროსი": 'x_studio_shesy_dep_ufros',
#             "შესყ.დეპ. ჯგუფი": 'x_studio_shesy_group_1',
#             "ბაზრის კვლევა და განფასება": 'x_studio_baz_kvleva_1',
#             "ფინანსური სამმართველო": 'x_studio_fin_samartv_1',
#             "ფინანსური დეპარტამენტი": 'x_studio_fin_dep_1',
#             "CPV კოდები": 'x_studio_cpv_user_1',
#             "ფინანსური დირექტორი": 'x_studio_dir_moadg_1',
#             "გენერალური დირექტორი": 'x_studio_gen_director_1',
#             "AUTO ფილ. კოორდ.": "x_studio_auto_fil_kord",
#             "AUTO სამმართ. უფროსი": "x_studio_auto_samart_ufros",
#             "AUTO ხელშ. ზედამხედველი": "x_studio_auto_xelsh_zedamx",
#             "AUTO სატრ. უზრ. სამმ. უფროსი": "x_studio_auto_uzr_sammart_ufors",
#             "AUTO დეპ. უფროსი": "x_studio_auto_dep_ufros",
#             "AUTO შესყ. დეპარტამენტი": "x_studio_auto_shesy_dep",
#         }
        
#         # Mark activities as done when leaving a stage
#         for stage_name, field_name in stage_field_mapping.items():
#             if old_stage_name == stage_name and new_stage_name != stage_name:
#                 user_field = getattr(self, field_name, False)
#                 if user_field:
#                     activities = self.env['mail.activity'].sudo().search([
#                         ('res_id', '=', self.id),
#                         ('res_model', '=', 'inventory.request'),
#                         ('user_id', 'in', user_field.ids)
#                     ])
#                     activities.action_done()
#                     _logger.info(f"Marked {len(activities)} activities as done for stage: {stage_name}")
        
#         # Create activities when entering a stage
#         for stage_name, field_name in stage_field_mapping.items():
#             if new_stage_name == stage_name and old_stage_name != stage_name:
#                 user_field = getattr(self, field_name, False)
#                 if user_field:
#                     self._create_activities_for_users(user_field, new_stage_name)
    
#     def _create_activities_for_users(self, users, stage_name):
#         """
#         Create activities for given users
#         """
#         # Get activity type (default to "Todo" type)
#         activity_type = self.env['mail.activity.type'].sudo().search([
#             ('name', '=', 'Todo')
#         ], limit=1)
        
#         if not activity_type:
#             activity_type = self.env['mail.activity.type'].sudo().search([], limit=1)
        
#         res_model_id = self.env['ir.model'].sudo().search([('model', '=', 'inventory.request')], limit=1).id
        
#         for user in users:
#             # Check if activity already exists for this user
#             existing_activity = self.env['mail.activity'].sudo().search([
#                 ('res_id', '=', self.id),
#                 ('res_model', '=', 'inventory.request'),
#                 ('user_id', '=', user.id)
#             ], limit=1)
            
#             if not existing_activity:
#                 # Create activity
#                 self.env['mail.activity'].sudo().create({
#                     'res_id': self.id,
#                     'res_model_id': res_model_id,
#                     'activity_type_id': activity_type.id if activity_type else False,
#                     'summary': f'Inventory Request - Stage: {stage_name}',
#                     'note': f'Action required for inventory request in stage "{stage_name}"',
#                     'user_id': user.id,
#                 })
#                 _logger.info(f"Created activity for user: {user.name} at stage: {stage_name}")

#     def write(self, vals):
#         if 'stage_id' in vals:
#             stage_id = vals['stage_id']
#             stage = self.env['inventory.request.stage'].sudo().browse(stage_id)
            
#             # Handle activity creation/completion based on stage change
#             old_stage_name = self.stage_id.name if self.stage_id else False
#             new_stage_name = stage.name
            
#             # Call the activity handler method
#             self._handle_stage_activities(old_stage_name, new_stage_name)
            
#             # raise UserError(f"stage_id: {stage_id} stage name: {stage.name} stage sequence: {stage.sequence} self.stage_id.sequence: {self.stage_id.name}")
#             if self.stage_id.sequence < stage.sequence:
#                 # Store the current user who is changing the stage
#                 approver_user = self.env.user
#                 # raise UserError(f"approver_user: {approver_user} approver user name: {self.env.user.name}")
#                 approve_datetime = datetime.now()
#                 # raise UserError(f"approve_datetime: {approve_datetime}")
#                 # approver_user_ids = []
                
#                 # for user in self.x_studio_many2many_field_9d8_1jcbd2e76:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_zemdgomi_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_filial_ufros_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_tech_dep_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_tech_director_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_whs_sam_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_logist_dep_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_logist_dir_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_shesy_dep_ufros:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_shesy_group_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_baz_kvleva_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_fin_samartv_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_fin_dep_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_cpv_user_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_dir_moadg_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_gen_director_1:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_auto_fil_kord:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_auto_samart_ufros:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_auto_xelsh_zedamx:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_auto_uzr_sammart_ufors:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_auto_dep_ufros:
#                 #     approver_user_ids.append(user.id)
#                 # for user in self.x_studio_auto_shesy_dep:
#                 #     approver_user_ids.append(user.id)
#                 approver_fields = [
#                     'x_studio_many2many_field_9d8_1jcbd2e76', 'x_studio_zemdgomi_1', 
#                     'x_studio_filial_ufros_1', 'x_studio_tech_dep_1', 'x_studio_tech_director_1',
#                     'x_studio_whs_sam_1', 'x_studio_logist_dep_1', 'x_studio_logist_dir_1',
#                     'x_studio_shesy_dep_ufros', 'x_studio_shesy_group_1', 'x_studio_baz_kvleva_1',
#                     'x_studio_fin_samartv_1', 'x_studio_fin_dep_1', 'x_studio_cpv_user_1',
#                     'x_studio_dir_moadg_1', 'x_studio_gen_director_1', 'x_studio_auto_fil_kord',
#                     'x_studio_auto_samart_ufros', 'x_studio_auto_xelsh_zedamx', 
#                     'x_studio_auto_uzr_sammart_ufors', 'x_studio_auto_dep_ufros', 'x_studio_auto_shesy_dep'
#                 ]
#                 approver_users = self.env['res.users']
#                 for field in approver_fields:
#                     approver_users |= self[field]

#                 # raise UserError(f"approver_user_ids: {approver_user_ids}")
#                 if approver_user.id in approver_users.ids:
#                     existing_approver_user = self.env['inventory.request.approver.users'].sudo().search([('user_id', '=', approver_user.id), ('inventory_request_id', '=', self.id)])
#                     if not existing_approver_user:
#                         employee = approver_user.employee_id
#                         self.env['inventory.request.approver.users'].sudo().create({
#                             'user_id': approver_user.id,
#                             'approve_datetime': approve_datetime,
#                             'job_position': employee.job_id.id if employee.job_id else False,
#                             'inventory_request_id': self.id,
#                         })
#         return super(InventoryRequest, self).write(vals)
from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    approver_users_ids = fields.One2many(
        'inventory.request.approver.users',
        'inventory_request_id',
        string='Approver Users'
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super(InventoryRequest, self).create(vals_list)
        ApproverModel = self.env['inventory.request.approver.users'].sudo()
        for record in records:
            if hasattr(record, 'requested_by') and record.requested_by:
                ApproverModel.create({
                    'is_first_approver': True,
                    'user_id': record.requested_by.id,
                    'approve_datetime': record.create_date,
                    'job_position': record.requested_by.employee_id.job_id.id if record.requested_by.employee_id and record.requested_by.employee_id.job_id else False,
                    'inventory_request_id': record.id,
                })
                _logger.info(f"Added requested_by as first approver: {record.requested_by.name}")
        return records

    def write(self, vals):
        # Define approver fields that trigger activity creation
        _logger.info(f"===============write===============")
        _logger.info(f"vals: {vals}")
        approver_fields = [
            'x_studio_many2many_field_9d8_1jcbd2e76', 'x_studio_zemdgomi_1',
            'x_studio_filial_ufros_1', 'x_studio_tech_dep_1', 'x_studio_tech_director_1',
            'x_studio_whs_sam_1', 'x_studio_logist_dep_1', 'x_studio_logist_dir_1',
            'x_studio_shesy_dep_ufros', 'x_studio_shesy_group_1', 'x_studio_baz_kvleva_1',
            'x_studio_fin_samartv_1', 'x_studio_fin_dep_1', 'x_studio_cpv_user_1',
            'x_studio_dir_moadg_1', 'x_studio_gen_director_1', 'x_studio_auto_fil_kord',
            'x_studio_auto_samart_ufros', 'x_studio_auto_xelsh_zedamx',
            'x_studio_auto_uzr_sammart_ufors', 'x_studio_auto_dep_ufros', 'x_studio_auto_shesy_dep'
        ]

        # Check if stage_id or any approver field is being changed
        stage_changed = 'stage_id' in vals
        approver_field_changed = any(field in vals for field in approver_fields)
        requested_by_changed = 'requested_by' in vals

        # Store old stage info BEFORE write (only if stage is changing)
        old_stage_info = {}
        if stage_changed:
            for record in self:
                old_stage_info[record.id] = {
                    'old_stage_name': record.stage_id.name if record.stage_id else False,
                    'old_sequence': record.stage_id.sequence if record.stage_id else 0,
                }

        # ✅ CALL SUPER FIRST - This populates user fields and does everything else
        result = super(InventoryRequest, self).write(vals)

        # When requested_by is changed: delete old first approver line and create new one
        if requested_by_changed:
            ApproverModel = self.env['inventory.request.approver.users'].sudo()
            for record in self:
                if not hasattr(record, 'requested_by'):
                    continue
                old_first = ApproverModel.search([
                    ('inventory_request_id', '=', record.id),
                    ('is_first_approver', '=', True)
                ])
                old_first.unlink()
                if record.requested_by:
                    employee = record.requested_by.employee_id
                    ApproverModel.create({
                        'is_first_approver': True,
                        'user_id': record.requested_by.id,
                        'approve_datetime': record.create_date or datetime.now(),
                        'job_position': employee.job_id.id if employee and employee.job_id else False,
                        'inventory_request_id': record.id,
                    })
                    _logger.info(f"Replaced first approver with requested_by: {record.requested_by.name}")

        # ✅ Handle changes AFTER write is complete
        if stage_changed or approver_field_changed:
            for record in self:
                current_stage_name = record.stage_id.name if record.stage_id else False
                
                if stage_changed:
                    # Stage was changed
                    old_data = old_stage_info.get(record.id, {})
                    old_stage_name = old_data.get('old_stage_name')
                    old_sequence = old_data.get('old_sequence', 0)
                    new_sequence = record.stage_id.sequence if record.stage_id else 0
                    
                    _logger.info(f"Stage changed from '{old_stage_name}' to '{current_stage_name}'")
                    
                    # Handle activities for stage change
                    record._handle_stage_activities(old_stage_name, current_stage_name)
                    
                    # Store approver info if moving forward
                    if old_sequence < new_sequence:
                        record._store_approver_info()
                
                elif approver_field_changed:
                    # Only approver fields changed (not stage)
                    _logger.info(f"Approver fields changed for stage: {current_stage_name}")
                    
                    # Recreate activities for current stage with new users
                    record._handle_stage_activities(None, current_stage_name)
        
        return result

    def action_approve(self):
        """
        Button "მომთხოვნების დადასტურება": add requested_by to approvers if not already there.
        Only ensures requested_by has an approver line with is_first_approver=True; no other logic.
        """
        ApproverModel = self.env['inventory.request.approver.users'].sudo()
        for record in self:
            if not hasattr(record, 'requested_by') or not record.requested_by:
                continue
            existing = ApproverModel.search([
                ('inventory_request_id', '=', record.id),
                ('user_id', '=', record.requested_by.id),
            ], limit=1)
            first_approver = ApproverModel.search([
                ('inventory_request_id', '=', record.id),
                ('is_first_approver', '=', True),
                ('user_id', '!=', record.requested_by.id)
            ], limit=1)
            if first_approver:
                first_approver.sudo().unlink()
            if existing:
                continue
            employee = record.requested_by.employee_id
            ApproverModel.create({
                'is_first_approver': True,
                'user_id': record.requested_by.id,
                'approve_datetime': record.create_date or datetime.now(),
                'job_position': employee.job_id.id if employee and employee.job_id else False,
                'inventory_request_id': record.id,
            })
        return True

    def _store_approver_info(self):
        """Store approver information when moving to next stage.
        requested_by (request creator) is ensured in the approvers list; they are first because
        they are added on create() so their approver line has the smallest id.
        """
        approver_user = self.env.user
        approve_datetime = datetime.now()
        ApproverModel = self.env['inventory.request.approver.users'].sudo()

        # 1. Ensure requested_by is in approvers list as first approver (for records created before this logic)
        if hasattr(self, 'requested_by') and self.requested_by:
            existing_first = ApproverModel.search([
                ('inventory_request_id', '=', self.id),
                ('is_first_approver', '=', True)
            ], limit=1)
            if not existing_first:
                employee = self.requested_by.employee_id
                ApproverModel.create({
                    'is_first_approver': True,
                    'user_id': self.requested_by.id,
                    'approve_datetime': self.create_date or approve_datetime,
                    'job_position': employee.job_id.id if employee and employee.job_id else False,
                    'inventory_request_id': self.id,
                })
                _logger.info(f"Stored requested_by in approvers list: {self.requested_by.name}")

        # Get all approver fields
        approver_fields = [
            'x_studio_many2many_field_9d8_1jcbd2e76', 'x_studio_zemdgomi_1',
            'x_studio_filial_ufros_1', 'x_studio_tech_dep_1', 'x_studio_tech_director_1',
            'x_studio_whs_sam_1', 'x_studio_logist_dep_1', 'x_studio_logist_dir_1',
            'x_studio_shesy_dep_ufros', 'x_studio_shesy_group_1', 'x_studio_baz_kvleva_1',
            'x_studio_fin_samartv_1', 'x_studio_fin_dep_1', 'x_studio_cpv_user_1',
            'x_studio_dir_moadg_1', 'x_studio_gen_director_1', 'x_studio_auto_fil_kord',
            'x_studio_auto_samart_ufros', 'x_studio_auto_xelsh_zedamx',
            'x_studio_auto_uzr_sammart_ufors', 'x_studio_auto_dep_ufros', 'x_studio_auto_shesy_dep'
        ]

        # Collect all authorized users
        approver_users = self.env['res.users']
        for field in approver_fields:
            if hasattr(self, field):
                approver_users |= self[field]

        # 2. Store current user if authorized
        if approver_user.id in approver_users.ids:
            existing_approver = ApproverModel.search([
                ('user_id', '=', approver_user.id),
                ('inventory_request_id', '=', self.id)
            ], limit=1)

            if not existing_approver:
                employee = approver_user.employee_id
                ApproverModel.create({
                    'user_id': approver_user.id,
                    'approve_datetime': approve_datetime,
                    'job_position': employee.job_id.id if employee and employee.job_id else False,
                    'inventory_request_id': self.id,
                })
                _logger.info(f"Stored approver: {approver_user.name}")

    def _handle_stage_activities(self, old_stage_name, new_stage_name):
        """Handle activity creation and completion based on stage changes"""
        _logger.info(f"===============_handle_stage_activities===============")
        _logger.info(f"old_stage_name: {old_stage_name} new_stage_name: {new_stage_name}")
        
        # Define stage-to-field mapping
        stage_field_mapping = {
            "ადგ. საწყობი": 'x_studio_many2many_field_9d8_1jcbd2e76',
            "ზემდგომი": 'x_studio_zemdgomi_1',
            "ფილიალის უფროსი": 'x_studio_filial_ufros_1',
            "დეპ. ხელმძღვანელი": 'x_studio_tech_dep_1',
            "ხელმძღვანელი": 'x_studio_tech_director_1',
            "სასაწყობე მეურ. სამმ.": 'x_studio_whs_sam_1',
            "ლოგისტიკის დეპარტამენტი": 'x_studio_logist_dep_1',
            "ლოგისტიკის დირექტორი": 'x_studio_logist_dir_1',
            "შესყ. დეპ. უფროსი": 'x_studio_shesy_dep_ufros',
            "შესყ.დეპ. ჯგუფი": 'x_studio_shesy_group_1',
            "ბაზრის კვლევა და განფასება": 'x_studio_baz_kvleva_1',
            "ფინანსური სამმართველო": 'x_studio_fin_samartv_1',
            "ფინანსური დეპარტამენტი": 'x_studio_fin_dep_1',
            "CPV კოდები": 'x_studio_cpv_user_1',
            "ფინანსური დირექტორი": 'x_studio_dir_moadg_1',
            "გენერალური დირექტორი": 'x_studio_gen_director_1',
            "AUTO ფილ. კოორდ.": "x_studio_auto_fil_kord",
            "AUTO სამმართ. უფროსი": "x_studio_auto_samart_ufros",
            "AUTO ხელშ. ზედამხედველი": "x_studio_auto_xelsh_zedamx",
            "AUTO სატრ. უზრ. სამმ. უფროსი": "x_studio_auto_uzr_sammart_ufors",
            "AUTO დეპ. უფროსი": "x_studio_auto_dep_ufros",
            "AUTO შესყ. დეპარტამენტი": "x_studio_auto_shesy_dep",
        }
        
        # Mark activities as done when leaving a stage
        if old_stage_name and new_stage_name and old_stage_name != new_stage_name:
            for stage_name, field_name in stage_field_mapping.items():
                if old_stage_name == stage_name:
                    user_field = getattr(self, field_name, False)
                    if user_field:
                        activities = self.env['mail.activity'].sudo().search([
                            ('res_id', '=', self.id),
                            ('res_model', '=', 'inventory.request'),
                            ('user_id', 'in', user_field.ids)
                        ])
                        activities.action_done()
                        _logger.info(f"Marked {len(activities)} activities as done for stage: {stage_name}")
        
        # Create activities when entering a stage OR when users are updated
        if new_stage_name:
            # Special AUTO stage: schedule activity for a fixed user by name
            if new_stage_name == 'AUTO შალვა ლობჟანიძე':
                target_user = self.env['res.users'].sudo().search(
                    [('name', '=', 'შალვა ლობჟანიძე')],
                    limit=1,
                )
                if target_user:
                    # Delete old activities for this stage first (avoid duplicates on re-entry)
                    old_activities = self.env['mail.activity'].sudo().search([
                        ('res_id', '=', self.id),
                        ('res_model', '=', 'inventory.request'),
                        ('summary', 'ilike', new_stage_name),
                    ])
                    old_activities.unlink()
                    self._create_activities_for_users(target_user, new_stage_name)
                else:
                    _logger.warning(
                        "User '%s' not found for stage '%s'",
                        'შალვა ლობჟანიძე',
                        new_stage_name,
                    )
            else:
                for stage_name, field_name in stage_field_mapping.items():
                    if new_stage_name == stage_name:
                        user_field = getattr(self, field_name, False)
                        if user_field:
                            _logger.info(f"Creating/updating activities for {len(user_field)} users in stage: {stage_name}")
                            
                            # Delete old activities for this stage first (to handle user changes)
                            old_activities = self.env['mail.activity'].sudo().search([
                                ('res_id', '=', self.id),
                                ('res_model', '=', 'inventory.request'),
                                ('summary', 'ilike', stage_name)
                            ])
                            old_activities.unlink()
                            
                            # Create new activities
                            self._create_activities_for_users(user_field, new_stage_name)
                        else:
                            _logger.warning(f"No users found in field '{field_name}' for stage: {stage_name}")
    
    def _create_activities_for_users(self, users, stage_name):
        """Create activities for given users"""
        # Get activity type (default to "Todo" type) from mail.activity.type
        activity_type = self.env['mail.activity.type'].sudo().search([
            ('name', '=', 'Todo')
        ], limit=1)
        
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().search([], limit=1)
        
        res_model_id = self.env['ir.model'].sudo().search([
            ('model', '=', 'inventory.request')
        ], limit=1).id
        
        for user in users:
            # Check if activity already exists for this user
            existing_activity = self.env['mail.activity'].sudo().search([
                ('res_id', '=', self.id),
                ('res_model', '=', 'inventory.request'),
                ('user_id', '=', user.id)
            ], limit=1)
            
            if not existing_activity:
                # Create activity
                self.env['mail.activity'].sudo().create({
                    'res_id': self.id,
                    'res_model_id': res_model_id,
                    'activity_type_id': activity_type.id if activity_type else False,
                    'summary': f'Inventory Request - Stage: {stage_name}',
                    'note': f'Action required for inventory request in stage "{stage_name}"',
                    'user_id': user.id,
                })
                _logger.info(f"Created activity for user: {user.name} at stage: {stage_name}")