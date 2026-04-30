from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from datetime import datetime, time




class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    # move_ids = fields.One2many(
    #     'account.move',
    #     'approval_request_id',
    #     string="Accounting Entries",
    # )


    time_off_days = fields.Integer(
        string="Time Off Days",
        compute="_compute_time_off_days",
        store=True,
    )

    accounting_generated = fields.Boolean(string="Accounting Generated", default=False)

    request_status = fields.Selection([
        ('new', 'შესასრულებლად'),
        #('order_preparation', 'ბრძანების მომზადება'),
        ('pending', 'დასადასტურებელი'),
        ('approved', 'ხელმოწერილი'),
        ('refused', 'უარყოფილი'),
        ('cancel', 'გაუქმებული')],
        string="სტატუსი",
        compute="_compute_request_status",
        store=True,
        tracking=True,
        help="სტატუსი."
    )


    @api.model
    def default_get(self, fields_list):
        defaults = super(ApprovalRequest, self).default_get(fields_list)
        if 'x_studio_approval_date' in fields_list:
            defaults['x_studio_approval_date'] = fields.Date.context_today(self)
        return defaults

    @api.depends('category_id', 'request_owner_id')
    def _compute_approver_ids(self):
        for request in self:
            # Re-implement logic to be additive instead of clearing existing approvers
            current_user_ids = set(request.approver_ids.mapped('user_id.id'))
            new_vals = []

            # 1. Add Manager if required/configured
            if request.category_id.manager_approval:
                employee = self.env['hr.employee'].search([('user_id', '=', request.request_owner_id.id)], limit=1)
                if employee.parent_id.user_id:
                    manager_id = employee.parent_id.user_id.id
                    if manager_id not in current_user_ids:
                        new_vals.append(Command.create({
                             'user_id': manager_id,
                             'status': 'new',
                             'required': request.category_id.manager_approval == 'required',
                             'sequence': 9,
                        }))
                        current_user_ids.add(manager_id)
            
            # 2. Add Category Defaults
            for approver in request.category_id.approver_ids:
                if approver.user_id.id not in current_user_ids:
                    new_vals.append(Command.create({
                        'user_id': approver.user_id.id,
                        'status': 'new',
                        'required': approver.required,
                        'sequence': approver.sequence,
                    }))
                    current_user_ids.add(approver.user_id.id)
            
            if new_vals:
                request.update({'approver_ids': new_vals})



    def action_confirm(self):
        super(ApprovalRequest, self).action_confirm()  
        for req in self:
            # Mark activities as done for the current user
            req.activity_ids.filtered(lambda a: a.user_id == self.env.user).action_feedback(feedback="Submitted")

    # employee_line_ids = fields.One2many(
    #     'approval.request.employee.line',
    #     'request_id',
    #     string="თანამშრომლები"
    # )

    transfer_department_id = fields.Many2one(
        'hr.department',
        string="ახალი დეპარტამენტი",
    )

    transfer_job_id = fields.Many2one(
        'hr.job',
        string="ახალი პოზიცია",
        domain="[('department_id', '=', transfer_department_id)]",
    )

    @api.onchange('transfer_department_id')
    def _onchange_transfer_department(self):
        for req in self:
            if req.transfer_job_id and req.transfer_job_id.department_id != req.transfer_department_id:
                req.transfer_job_id = False
            for line in req.premia_line_ids:
                line.new_department_id = req.transfer_department_id

    @api.onchange('transfer_job_id')
    def _onchange_transfer_job(self):
        for req in self:
            for line in req.premia_line_ids:
                line.new_job_id = req.transfer_job_id
                if req.transfer_job_id:
                    line.new_wage = req.transfer_job_id.expected_salary
                else:
                    line.new_wage = 0.0

    premia_line_ids = fields.One2many(
        'approval.premia.line',
        'request_id',
        string="Premia Lines"
    )

    premia_lines_count = fields.Integer(
        string="თანამშრომლების რაოდენობა",
        compute="_compute_premia_lines_count",
        store=True,
    )

    @api.depends('premia_line_ids')
    def _compute_premia_lines_count(self):
        for req in self:
            req.premia_lines_count = len(req.premia_line_ids)

    adresati_ids = fields.Many2many(
        'res.users',
        string="ადრესატები",
        help="მომხმარებლები, ვინც მიიღებენ შეტყობინებას ხელმოწერის ბოლოს."
    )

    # approver_line_ids = fields.One2many(
    #     'approval.request.approver.line',
    #     'request_id',
    #     string="Approver Lines"
    # )
    # can_forward_line = fields.Boolean(compute="_compute_can_forward_line")

    # def _compute_can_forward_line(self):
    #     for req in self:
    #         # Check if current user is in approver_line_ids (and active?)
    #         # Logic: If user is in the list, they can forward. 
    #         # You might want to restrict to 'new' or 'pending', 
    #         # but usually forwarding is allowed if you are involved.
    #         is_approver_line = req.approver_line_ids.filtered(
    #             lambda a: a.user_id.id == req.env.uid
    #         )
    #         req.can_forward_line = bool(is_approver_line)

    # can_prepare_order = fields.Boolean(compute="_compute_can_prepare_order")
    
    # is_order_preparation = fields.Boolean(string="Is in Preparation", default=False, copy=False)

    # def _compute_can_prepare_order(self):
    #     for req in self:
    #         # Check if current user has a 'new' approver line
    #         is_new_approver = req.approver_line_ids.filtered(
    #             lambda a: a.user_id.id == req.env.uid and a.status == 'new'
    #         )
    #         req.can_prepare_order = bool(is_new_approver)

    def write(self, vals):
        # Check if 'signed_document' is being set
        trigger_adresati = False
        if 'signed_document' in vals and vals['signed_document']:
            trigger_adresati = True
        
        res = super(ApprovalRequest, self).write(vals)

        if trigger_adresati:
            for req in self:
                if req.adresati_ids:
                    # Notify them
                    for user in req.adresati_ids:
                         req.activity_schedule(
                            'mail.mail_activity_data_todo',
                            user_id=user.id,
                            summary=f"ბრძანება დადასტურდა: {req.name}",
                            note="ბრძანება დადასტურდა."
                        )
        return res



    def action_draft(self):
        res = super(ApprovalRequest, self).action_draft()
        # self.write({'is_order_preparation': False})
        return res

    @api.depends(
        'approver_ids.status',
        'approver_ids.required',
        'signed_document',
    )
    def _compute_request_status(self):
        # Let base approvals logic run first
        super()._compute_request_status()

        for request in self:
             # Persist order_preparation if flag is set and base logic thinks it's new
            # if request.is_order_preparation and request.request_status == 'new':
            #      request.request_status = 'order_preparation'

             # Block final approval until document is signed
            if request.request_status == 'approved' and not request.signed_document:
                request.request_status = 'pending'
    

   # def _compute_can_forward(self):
   #     for req in self:
   #         approver = req.approver_ids.filtered(
   #             lambda a: a.user_id.id == req.env.uid
   #             and a.status in ('new', 'pending', 'waiting')
   #         )[:1]
   #         req.can_forward = bool(approver)



    @api.depends(
        'x_studio_employee_new',
        'x_studio_contract_start',
        'x_studio_contract_end',
        'x_studio_time_off_type',
    )
    def _compute_time_off_days(self):
        Leave = self.env['hr.leave']

        for req in self:
            req.time_off_days = 0.0

            if not (
                req.x_studio_employee_new
                and req.x_studio_contract_start
                and req.x_studio_contract_end
                and req.x_studio_time_off_type
            ):
                continue

            # 1️⃣ Create a VIRTUAL hr.leave (not saved)
            leave = Leave.new({
                'employee_id': req.x_studio_employee_new.id,
                'holiday_status_id': req.x_studio_time_off_type.id,
                'request_date_from': req.x_studio_contract_start,
                'request_date_to': req.x_studio_contract_end,
            })

            # 2️⃣ Let Odoo compute everything
            leave._compute_date_from_to()
            leave._compute_duration()

            # 3️⃣ Read the result
            req.time_off_days = leave.number_of_days





    @api.onchange('x_studio_departmenti', 'x_studio_job_posit')
    def _onchange_studio_premia_filters(self):
        for req in self:
            # Clear lines when changing
            req.premia_line_ids = [Command.clear()]

            # Determine if we should populate employees
            domain = []
            has_filter = False
            
            # Use getattr to safely access Studio fields without defining them in Python
            dept = getattr(req, 'x_studio_departmenti', False)
            if dept:
                domain.append(('department_id', '=', dept.id))
                has_filter = True
                
            job = getattr(req, 'x_studio_job_posit', False)
            if job:
                domain.append(('job_id', '=', job.id))
                has_filter = True
                
            if has_filter:
                employees = self.env['hr.employee'].search(domain)
                lines = []
                for emp in employees:
                    lines.append(Command.create({
                        'employee_id': emp.id,
                    }))
                req.premia_line_ids = lines


    def _trigger_adresati_after_approve(self):
        """Automatically add adresati as approver when all adresatamde approvers are approved."""
        self.ensure_one()

        adresati_user = self.x_studio_adresati
        if not adresati_user:
            return

        # find approvers with adresatamde = True
        adresatamde_approvers = self.approver_ids.filtered(lambda a: a.adresatamde)

        # condition: we have such approvers AND they are all approved
        if adresatamde_approvers and all(a.status == 'approved' for a in adresatamde_approvers):

            # check if notification already sent to prevent spam
            existing_activity = self.activity_ids.filtered(
                lambda a: a.user_id.id == adresati_user.id and a.summary == "გთხოვთ მოაწეროთ ხელი"
            )
            
            if not existing_activity:
                # notify adresati
                self.env['mail.activity'].create({
                    'activity_type_id': self.env.ref('approvals.mail_activity_data_approval').id,
                    'res_model_id': self.env.ref('approvals.model_approval_request').id,
                    #'calendar_type': 'other',
                    'res_id': self.id,
                    'user_id': adresati_user.id,
                    'summary': "გთხოვთ მოაწეროთ ხელი",
                    'date_deadline': fields.Date.today(),
                })


    def action_approve(self):
        res = super(ApprovalRequest, self).action_approve()

        # After normal approval – check if adresati should be added
        for req in self:
            req._trigger_adresati_after_approve()

        return res                               


# class ApprovalRequestEmployeeLine(models.Model):
#     _name = 'approval.request.employee.line'
#     _description = 'Approval Request Employee Line'

#     request_id = fields.Many2one(
#         'approval.request',
#         string="Approval Request",
#         ondelete='cascade'
#     )

#     employee_id = fields.Many2one(
#         'hr.employee',
#         string="თანამშრომელი",
#         required=True
#     )

#     note = fields.Char(string="შენიშვნა")



class ApprovalPremiaLine(models.Model):
    _name = 'approval.premia.line'
    _description = 'Approval Premia Line'

    request_id = fields.Many2one(
        'approval.request',
        string="Approval Request",
        ondelete='cascade',
        required=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="თანამშრომელი",
        required=True
    )

    @api.depends('employee_id')
    def _compute_employee_details(self):
        for line in self:
            if line.employee_id:
                line.department_id = line.employee_id.department_id.id
                line.job_id = line.employee_id.job_id.id
                # Attempt to get contract wage safely
                if hasattr(line.employee_id, 'contract_id') and line.employee_id.contract_id:
                    line.current_wage = line.employee_id.contract_id.wage
                else:
                    line.current_wage = 0.0
            else:
                line.department_id = False
                line.job_id = False
                line.current_wage = 0.0

    department_id = fields.Many2one(
        'hr.department',
        string="დეპარტამენტი",
        compute='_compute_employee_details',
        store=True,
        readonly=False
    )

    job_id = fields.Many2one(
        'hr.job',
        string="პოზიცია",
        compute='_compute_employee_details',
        store=True,
        readonly=False
    )

    current_wage = fields.Float(
        string="მიმდინარე ხელფასი",
        compute='_compute_employee_details',
        store=True,
        readonly=False
    )

    new_wage = fields.Float(
        string="ახალი ხელფასი"
    )

    new_department_id = fields.Many2one(
        'hr.department',
        string="ახალი დეპარტამენტი",
    )

    new_job_id = fields.Many2one(
        'hr.job',
        string="ახალი პოზიცია",
        domain="[('department_id', '=', new_department_id)]",
    )

    @api.onchange('new_job_id')
    def _onchange_new_job_id(self):
        for line in self:
            if line.new_job_id:
                line.new_wage = line.new_job_id.expected_salary
            else:
                line.new_wage = 0.0


# class ApprovalRequestApproverLine(models.Model):
#     _name = 'approval.request.approver.line'
#     _description = 'Approval Request Approver Line'

#     request_id = fields.Many2one(
#         'approval.request',
#         string="Approval Request",
#         ondelete='cascade',
#         required=True
#     )

#     user_id = fields.Many2one(
#         'res.users',
#         string="მომხმარებელი",
#         required=True
#     )

#     status = fields.Selection([
#         ('new', 'New'),
#         ('pending', 'To Approve'),
#         ('approved', 'Approved'),
#         ('refused', 'Refused'),
#         ('cancel', 'Cancel')],
#         string="სტატუსი",
#         default='new',
#         readonly=True
#     )
    
    # role = fields.Char(string="Role")
    
    #required = fields.Boolean(default=True, string="Required")


class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'
    #adresatamde = fields.Boolean(string="ადრესატამდე")

    adresatamde = fields.Boolean(
        string="ადრესატამდე",
        default=True
    )

    required = fields.Boolean(
        default=True
    )




    







# class ApprovalLineForwardWizard(models.TransientModel):
#     _name = 'approval.line.forward.wizard'
#     _description = 'Forward Approval Line Wizard'

#     request_id = fields.Many2one('approval.request', required=True)
    
#     user_ids = fields.Many2many(
#         'res.users',
#         string="Users",
#         required=True
#     )
    
    
#     # role = fields.Char(string="Role", default="Forwarded")

#     def action_forward(self):
#         req = self.request_id
#         current_user = self.env.user
        
#         # 1. Approve the forwarder (current user)
#         current_line = req.approver_line_ids.filtered(lambda l: l.user_id.id == current_user.id)
#         if current_line:
#             current_line.write({'status': 'approved'})

#         # Mark activity as done for current user
#         req.activity_ids.filtered(lambda a: a.user_id == current_user).action_feedback(feedback="გადაწერილია")

#         for user in self.user_ids:
#             # Create new approver line
#             req.approver_line_ids.create({
#                 'request_id': req.id,
#                 'user_id': user.id,
#                 'status': 'new',
#                 # 'role': self.role,
#                 #'required': True, # or True?
#             })
            
#             # Subscribe to document
#             req.message_subscribe(partner_ids=user.partner_id.ids)
            
#             # Send notification
#             req.activity_schedule(
#                 'mail.mail_activity_data_todo',
#                 user_id=user.id,
#                 summary=f"თქვენ გადმოგეწერათ: {req.name}",
#                 note="გთხოვთ გადახედოთ"
#             )
            
#         return {'type': 'ir.actions.act_window_close'}


#class AccountMove(models.Model):
#    _inherit = 'account.move'

#    approval_request_id = fields.Many2one(
#        'approval.request',
#        string="Approval Request",
#        ondelete='set null'
#    )


