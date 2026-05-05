from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


class Moxsenebiti(models.Model):
    _name = "moxsenebiti"
    _description = "მოხსენებითი"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _rec_name = "number"

    # -----------------------------
    # Core fields
    # -----------------------------
    category_id = fields.Many2one("moxsenebiti.category", string="კატეგორია", required=True, tracking=True, ondelete="restrict")
    category_code = fields.Char(related="category_id.code", store=True, readonly=True)
    category_image = fields.Binary(related="category_id.image", readonly=True)

    number = fields.Char(string="მოხსენების ნომერი", readonly=True, copy=False, default="/", tracking=True)
    name = fields.Char(string="Name", readonly=True, copy=False, default="/", tracking=True)

    request_owner_id = fields.Many2one(
        "res.users", string="ინიციატორი",
        default=lambda self: self.env.user, required=True, readonly=True, tracking=True
    )
    
    x_studio_moxsenebiti_to_edit = fields.Many2one(
        "moxsenebiti", 
        string="რედაქტირებული მოხსენება", 
        domain=lambda self: [
            ('category_id', '=', 1), 
            ('generated_approval_id', '!=', False), 
            ('generated_approval_id.request_status', '=', 'approved'), 
            '|', '|', '|', '|', '|', '|', 
            ('request_owner_id', '=', self.env.user.id), 
            ('author_id', '=', self.env.user.id), 
            ('adresati_id', '=', self.env.user.id), 
            ('order_receiver_ids', 'in', [self.env.user.id]), 
            ('order_receiver_id', '=', self.env.user.id), 
            ('x_studio_transport_disp', '=', self.env.user.id), 
            ('approver_line_ids.user_id', '=', self.env.user.id)
        ]
    )

    author_id = fields.Many2one("res.users", string="ავტორი (ხელმომწერი)", tracking=True)
    adresati_id = fields.Many2one("res.users", string="ადრესატი", tracking=True)

    start_date = fields.Date(string="დაწყების თარიღი", tracking=True)
    end_date = fields.Date(string="დასრულების თარიღი", tracking=True)
    comment = fields.Text(string="მივლინების მიზანი")
    
    # Shvebuleba Fields
    leave_employee_id = fields.Many2one("hr.employee", string="თანამშრომელი")
    time_off_type_id = fields.Many2one("hr.leave.type", string="შვებულების ტიპი")
    time_off_days = fields.Float(string="დღეების რაოდენობა", compute="_compute_time_off_days")
    leaves_left = fields.Float(string="ნაშთი", compute="_compute_leaves_left")

    adresati_id = fields.Many2one("res.users", string="ადრესატი")

    word_file = fields.Binary(string="Word დოკუმენტი", attachment=True)
    word_filename = fields.Char(string="Word ფაილის სახელი")

    # -----------------------------
    # Lines
    # -----------------------------
    approver_line_ids = fields.One2many("moxsenebiti.approver.line", "moxsenebiti_id", string="ვიზა", copy=True)
    employee_line_ids = fields.One2many("moxsenebiti.employee.line", "moxsenebiti_id", string="დეტალიზაცია", copy=True)

    # -----------------------------
    # Transport sub-flow
    # -----------------------------
    # x_studio_transporti (Boolean) and x_studio_transport_disp (Many2one res.users)
    # are added via Studio and already exist in the DB.
    # We track the sub-phase with transport_state:
    #   none                  - transport flag off or not applicable
    #   pending_dispatch      - all regular approvers done; waiting for dispatcher to add vehicles
    #   pending_transport_appr- dispatcher submitted; waiting for transport approvers
    #   done                  - transport approvers all approved; author can now sign
    transport_state = fields.Selection(
        [
            ('none', 'N/A'),
            ('pending_dispatch', 'Dispatcher-ის მოლოდინი'),
            ('pending_transport_appr', 'სატრანსპორტო ვიზირება'),
            ('done', 'დასრულებული'),
        ],
        string="სატრანსპორტო ეტაპი",
        default='none',
        tracking=True,
    )

    # -----------------------------
    # Approval-like state machine (computed)
    # draft -> sent -> signed -> order_sent / rejected
    # "sent" itself is computed from: submitted + approvers pending/done
    # -----------------------------
    state = fields.Selection(
        [
            ("draft", "დრაფტი"),
            ("sent", "გადაგზავნილი"),         # means "in approval / waiting / approved but not signed"
            ("signed", "ხელმოწერილი"),
            ("order_sent", "გადაწერილი"),
            ("rejected", "უარყოფილი"),
            ("seen", "ნანახი"),
        ],
        string="სტატუსი",
        default="draft",
        tracking=True,
        required=True,
        group_expand="_expand_states"
    )

    @api.model
    def _expand_states(self, states, domain, order=None):
        return ["draft", "sent", "signed", "order_sent", "rejected", "seen"]

    # helper fields
    signed_document = fields.Boolean(string="Signed", default=False, tracking=True)

    current_approver_id = fields.Many2one("res.users", compute="_compute_current_approver", store=False)
    all_approved = fields.Boolean(compute="_compute_all_approved", store=False)

    # role flags for buttons
    is_current_approver = fields.Boolean(compute="_compute_roles", store=False)
    is_author_user = fields.Boolean(compute="_compute_roles", store=False)
    is_adresati_user = fields.Boolean(compute="_compute_roles", store=False)
    is_order_receiver_user = fields.Boolean(compute="_compute_roles", store=False)
    is_transport_disp = fields.Boolean(compute="_compute_roles", store=False)

    # button availability
    can_send = fields.Boolean(compute="_compute_buttons", store=False)
    can_approve = fields.Boolean(compute="_compute_buttons", store=False)
    can_reject = fields.Boolean(compute="_compute_buttons", store=False)
    can_sign = fields.Boolean(compute="_compute_buttons", store=False)
    can_send_to_order = fields.Boolean(compute="_compute_buttons", store=False)
    can_dispatch = fields.Boolean(compute="_compute_buttons", store=False)
    can_change_owner = fields.Boolean(compute="_compute_buttons", store=False)
    can_reinitiate = fields.Boolean(compute="_compute_buttons", store=False)
    can_manage_approvers = fields.Boolean(compute="_compute_buttons", store=False)

    # -----------------------------
    # Mivlineba fields
    # -----------------------------
    mivlineba_type = fields.Selection(
        [
            ("sazgvargaret", "საზღვარგარეთ"),
            ("gazificireba", "გაზიფიცირება"),
            ("tranziti", "ტრანზიტი"),
            ("sakhelsh", "სახელშეკრულებო"),
            ("zogadi", "ზოგადი"),
        ],
        string="მივლინების ტიპი",
        tracking=True,
    )

    stay_type = fields.Selection(
        [("with_night", "ღამის თევით"), ("without_night", "ღამის თევის გარეშე")],
        string="დარჩენის ტიპი",
        tracking=True,
    )

    x_studio_advance_pay = fields.Boolean(string="ავანსი", tracking=True)
    x_studio_invoice = fields.Boolean(string="ინვოისი", tracking=True)
    for_accounting = fields.Boolean(
        string="ბუღალტერიისთვის",
        tracking=True,
        help="თუ მონიშნულია, ხელმოწერის შემდეგ ეს მოხსენებითი დაემატება რეესტრში 'განახლების' დაჭერისას.",
    )
    
    # -----------------------------
    # HR Admin / Order Separation
    # -----------------------------
    order_receiver_id = fields.Many2one("res.users", string="ბრძანების მიმღები (Old)", tracking=True)
    order_receiver_ids = fields.Many2many("res.users", string="ბრძანების მიმღები", tracking=True)
    generated_approval_id = fields.Many2one("approval.request", string="გენერირებული ბრძანება", readonly=True, copy=False)

    @api.model
    def default_get(self, fields_list):
        res = super(Moxsenebiti, self).default_get(fields_list)
        if res.get('category_id') == 5:
            res['time_off_type_id'] = 2
        return res

    @api.onchange('category_id')
    def _onchange_category_id_set_default(self):
        if self.category_id.id == 5:
            self.time_off_type_id = 2

    @api.onchange('x_studio_moxsenebiti_to_edit')
    def _onchange_moxsenebiti_to_edit(self):
        source = self.x_studio_moxsenebiti_to_edit
        if source:
            self.start_date = source.start_date
            self.end_date = source.end_date
            self.mivlineba_type = source.mivlineba_type
            self.stay_type = source.stay_type
            self.comment = source.comment
            self.x_studio_advance_pay = source.x_studio_advance_pay
            self.x_studio_invoice = source.x_studio_invoice
            # Rebuild employee lines from source
            new_lines = []
            for line in source.employee_line_ids:
                new_lines.append((0, 0, {
                    'employee_id': line.employee_id.id,
                    'car_id': line.car_id.id,
                    'km': line.km,
                    'moto_hours': line.moto_hours,
                }))
            self.employee_line_ids = [(5, 0, 0)] + new_lines
        else:
            self.start_date = False
            self.end_date = False
            self.mivlineba_type = False
            self.stay_type = False
            self.comment = False
            self.x_studio_advance_pay = False
            self.x_studio_invoice = False
            self.employee_line_ids = [(5, 0, 0)]

    @api.onchange('x_studio_time_off_id')
    def _onchange_x_studio_time_off_id(self):
        if self.x_studio_time_off_id:
            self.time_off_type_id = self.x_studio_time_off_id.holiday_status_id

    @api.onchange('x_studio_transporti')
    def _onchange_x_studio_transporti(self):
        if not hasattr(self, 'x_studio_transporti') or not hasattr(self, 'x_studio_transport_disp'):
            return
            
        for rec in self:
            if rec.x_studio_transporti:
                primary_user_id = 18
                fallback_user_id = 122  # TODO: შეცვალეთ ალტერნატიული იუზერის ID-ით (თუ 18 შვებულებაშია)
                
                primary_user = rec.env['res.users'].browse(primary_user_id)
                assigned_id = primary_user_id
                
                if primary_user.exists() and primary_user.employee_id:
                    today = fields.Date.context_today(rec)
                    leaves_count = rec.env['hr.leave'].search_count([
                        ('employee_id', '=', primary_user.employee_id.id),
                        ('state', '=', 'validate'),
                        ('request_date_from', '<=', today),
                        ('request_date_to', '>=', today),
                    ])
                    if leaves_count > 0:
                        assigned_id = fallback_user_id
                        
                rec.x_studio_transport_disp = rec.env['res.users'].browse(assigned_id)
            else:
                rec.x_studio_transport_disp = False

    mivlineba_days = fields.Integer(string="დღეები", compute="_compute_mivlineba_days", store=True)

    @api.depends("start_date", "end_date")
    def _compute_mivlineba_days(self):
        for rec in self:
            rec.mivlineba_days = 0
            if rec.start_date and rec.end_date:
                delta = (rec.end_date - rec.start_date).days
                rec.mivlineba_days = delta + 1 if delta >= 0 else 0

    @api.depends("start_date", "end_date", "leave_employee_id", "time_off_type_id")
    def _compute_time_off_days(self):
        Leave = self.env['hr.leave']
        for req in self:
            req.time_off_days = 0.0
            if not (req.leave_employee_id and req.start_date and req.end_date and req.time_off_type_id):
                continue
            
            # Create VIRTUAL hr.leave
            leave = Leave.new({
                'employee_id': req.leave_employee_id.id,
                'holiday_status_id': req.time_off_type_id.id,
                'request_date_from': req.start_date,
                'request_date_to': req.end_date,
            })
            leave._compute_date_from_to()
            leave._compute_duration()
            req.time_off_days = leave.number_of_days

    @api.depends("leave_employee_id", "time_off_type_id")
    def _compute_leaves_left(self):
        for req in self:
            req.leaves_left = 0.0
            if req.leave_employee_id and req.time_off_type_id:
                # Get remaining leaves for this type/employee
                allocations = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', req.leave_employee_id.id),
                    ('holiday_status_id', '=', req.time_off_type_id.id),
                    ('state', '=', 'validate')
                ])
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', req.leave_employee_id.id),
                    ('holiday_status_id', '=', req.time_off_type_id.id),
                    ('state', '=', 'validate')
                ])
                # WE ASSUME DAYS for now (number_of_days)
                total_allocated = sum(allocations.mapped('number_of_days'))
                total_used = sum(leaves.mapped('number_of_days'))
                req.leaves_left = total_allocated - total_used

    # -----------------------------
    # Computations: current approver, all approved, roles, buttons
    # -----------------------------
    @api.depends("approver_line_ids.state", "approver_line_ids.sequence")
    def _compute_current_approver(self):
        # Parallel: useless to have single field, but keeping it empty/compatible
        for rec in self:
            rec.current_approver_id = False

    @api.depends("approver_line_ids.state", "transport_state", "category_code")
    def _compute_all_approved(self):
        for rec in self:
            # Determine if transport sub-flow applies
            transport_applies = (
                hasattr(rec, 'x_studio_transporti') and
                rec.x_studio_transporti and
                rec.category_code == 'mivlineba'
            )
            if not rec.approver_line_ids:
                # if transport_applies:
                #     # All regular approvers done (none) but transport must complete
                #     rec.all_approved = rec.transport_state == 'done'
                # else:
                #     rec.all_approved = True
                rec.all_approved = True
            else:
                regular_lines = rec.approver_line_ids.filtered(lambda l: l.approver_type == 'regular')
                transport_lines = rec.approver_line_ids.filtered(lambda l: l.approver_type == 'transport')
                # If no type set yet (legacy/no-type lines), treat all as regular
                if not regular_lines and not transport_lines:
                    all_regular_done = not rec.approver_line_ids.filtered(lambda l: l.state != 'approved')
                else:
                    all_regular_done = not regular_lines.filtered(lambda l: l.state != 'approved')

                # if transport_applies:
                #     # Need both: regular approved + transport phase completed
                #     rec.all_approved = all_regular_done and rec.transport_state == 'done'
                # else:
                #     rec.all_approved = all_regular_done
                rec.all_approved = all_regular_done

    @api.depends("approver_line_ids.state", "approver_line_ids.user_id", "author_id", "adresati_id", "transport_state")
    def _compute_roles(self):
        uid = self.env.user.id
        for rec in self:
            # Parallel: user is approver if they have a line in 'waiting' state
            waiting_approvers = rec.approver_line_ids.filtered(lambda l: l.state == 'waiting').mapped('user_id.id')
            rec.is_current_approver = uid in waiting_approvers

            rec.is_author_user = bool(rec.author_id and rec.author_id.id == uid)
            rec.is_adresati_user = bool(rec.adresati_id and rec.adresati_id.id == uid)
            rec.is_order_receiver_user = (
                (rec.order_receiver_id and rec.order_receiver_id.id == uid) or
                (uid in rec.order_receiver_ids.ids)
            )
            # Transport dispatcher: current user is x_studio_transport_disp AND we are waiting for them
            transport_disp_id = False
            if hasattr(rec, 'x_studio_transport_disp') and rec.x_studio_transport_disp:
                transport_disp_id = rec.x_studio_transport_disp.id
            rec.is_transport_disp = (
                transport_disp_id == uid and
                rec.transport_state == 'pending_dispatch'
            )

    @api.depends("order_receiver_ids")
    def _compute_has_multiple_receivers(self):
         for rec in self:
             rec.has_multiple_receivers = bool(rec.order_receiver_ids)

    has_multiple_receivers = fields.Boolean(compute="_compute_has_multiple_receivers")

    @api.depends("state", "is_current_approver", "is_author_user", "is_adresati_user", "all_approved", "signed_document", "is_transport_disp", "transport_state", "is_order_receiver_user")
    def _compute_buttons(self):
        for rec in self:
            rec.can_send = rec.state == "draft"
            # Parallel: any waiting approver can approve/reject
            # But NOT if they are a transport approver and we haven't reached that phase
            # (transport approvers' lines won't have state='waiting' until dispatch wizard runs)
            rec.can_approve = rec.state == "sent" and rec.is_current_approver
            
            # Reject: 
            # - sent: current approver OR author OR adresati
            # - signed: adresati (as they are the one to send to order next)
            can_reject_sent = rec.state == "sent" and (rec.is_current_approver or rec.is_author_user or rec.is_adresati_user)
            can_reject_signed = rec.state == "signed" and rec.is_adresati_user
            rec.can_reject = can_reject_sent or can_reject_signed

            # author signs only after all approved (transport_state='done' if transport applies)
            rec.can_sign = rec.state == "sent" and rec.is_author_user and rec.all_approved and not rec.signed_document
            # adresati sends to order only after signed
            rec.can_send_to_order = rec.state == "signed" and rec.is_adresati_user
            # Transport dispatcher can open dispatch wizard only when it's their turn
            rec.can_dispatch = rec.state == "sent" and rec.is_transport_disp
            rec.can_change_owner = rec.state == "draft" and rec.request_owner_id.id == self.env.user.id and bool(getattr(rec, 'x_studio_moxsenebiti_to_edit', False))
            rec.can_reinitiate = rec.state in ("signed", "order_sent") and rec.is_order_receiver_user and not rec.generated_approval_id

            is_owner_or_author = (
                (rec.request_owner_id and rec.request_owner_id.id == self.env.user.id)
                or (rec.author_id and rec.author_id.id == self.env.user.id)
            )
            rec.can_manage_approvers = (
                rec.state == "sent"
                and not rec.signed_document
                and (is_owner_or_author or self.env.user.has_group("base.group_system"))
            )

    # -----------------------------
    # Create: per-category numbering + name=number
    # -----------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("number", "/") in (False, "/", ""):
                if not vals.get("category_id"):
                    raise UserError(_("Please select Category first (needed for numbering)."))
                category = self.env["moxsenebiti.category"].browse(vals["category_id"])
                if not category.sequence_id:
                    raise UserError(_("Category '%s' has no Sequence configured.") % category.display_name)
                vals["number"] = category.sequence_id.next_by_id()

            if vals.get("name", "/") in (False, "/", ""):
                vals["name"] = vals.get("number") or "/"

        return super().create(vals_list)

    # =========================================================
    # Activities (Approvals style)
    # =========================================================
    def _approval_activity_type(self):
        # Same activity type as approvals
        return self.env.ref("approvals.mail_activity_data_approval", raise_if_not_found=False) or \
               self.env.ref("mail.mail_activity_data_todo")

    def _create_activity_for_user(self, user, summary, note=None):
        self.ensure_one()
        if not user:
            return
        at = self._approval_activity_type()
        # avoid duplicates
        existing = self.env["mail.activity"].search_count([
            ("res_model", "=", self._name),
            ("res_id", "=", self.id),
            ("user_id", "=", user.id),
            ("activity_type_id", "=", at.id),
            ("summary", "=", summary),
        ])
        if existing:
            return
        self.activity_schedule(
            activity_type_id=at.id,
            user_id=user.id,
            summary=summary,
            note=note or "",
            date_deadline=fields.Date.today(),
        )

    def _done_activity_for_user(self, user, summary):
        self.ensure_one()
        if not user:
            return
        at = self._approval_activity_type()
        acts = self.activity_ids.filtered(
            lambda a: a.user_id.id == user.id and a.activity_type_id.id == at.id and a.summary == summary
        )
        if acts:
            acts.action_feedback(_("Done"))

    def _notify_approvers(self):
        """Notify ALL waiting approvers."""
        self.ensure_one()
        waiting_lines = self.approver_line_ids.filtered(lambda l: l.state == 'waiting')
        for line in waiting_lines:
            if line.user_id:
                self._create_activity_for_user(
                    line.user_id,
                    summary="მოხსენება - დადასტურება",
                    note=_("გთხოვთ დაადასტუროთ მოხსენება: %s") % self.display_name,
                )

    def _notify_transport_disp(self):
        """Notify the transport dispatcher to add vehicles and submit to transport approvers."""
        self.ensure_one()
        disp = getattr(self, 'x_studio_transport_disp', False)
        if not disp:
            return
        self._create_activity_for_user(
            disp,
            summary="ვიზირება - ტრანსპორტი",
            note=_(
                "გთხოვთ დაამატოთ საჭირო ავტომობილები და გადაუგზავნოთ სატრანსპორტო "
                "ვიზიტორებს მოხსენებაზე: %s"
            ) % self.display_name,
        )

    def _notify_author_to_sign(self):
        self.ensure_one()
        if self.author_id:
            # try sign document automatically with author user if owner_id and author_id is same
            if self.request_owner_id and self.request_owner_id.id == self.author_id.id:
                try:
                    with self.env.cr.savepoint():
                        self.with_user(self.author_id.id).action_sign()
                except Exception:
                    pass
                    
            if self.state != 'signed':
                self._create_activity_for_user(
                    self.author_id,
                    summary="მოხსენება - ხელმოწერა",
                    note=_("გთხოვთ ხელი მოაწეროთ მოხსენებას: %s") % self.display_name,
                )

    def _notify_adresati(self):
        self.ensure_one()
        if self.adresati_id:
            self._create_activity_for_user(
                self.adresati_id,
                summary="მოხსენება - გადაწერა",
                note=_("გთხოვთ გადაწერა გააკეთოთ მოხსენებაზე: %s") % self.display_name,
            )

    # =========================================================
    # Actions (flow: approvers -> author -> adresati)
    # =========================================================
    def action_send(self):
        for rec in self:
            if rec.state != "draft":
                continue

            # Reset transport sub-flow state
            rec.transport_state = 'none'

            if not rec.approver_line_ids:
                 # No approvers — check transport flag
                 transport_applies = (
                     hasattr(rec, 'x_studio_transporti') and
                     rec.x_studio_transporti and
                     rec.category_code == 'mivlineba'
                 )
                 # if transport_applies:
                 #     rec.transport_state = 'pending_dispatch'
                 # else: no approvers, no transport → directly approved
            else:
                 # Parallel: ALL lines waiting
                 rec.approver_line_ids.write({"state": "waiting", "decision_date": False})

            rec.state = "sent"
            rec.signed_document = False
            rec.message_post(body=_("გაგზავნილია დასადასტურებლად."))
            
            if rec.approver_line_ids:
                rec._notify_approvers()
            else:
                transport_applies = (
                    hasattr(rec, 'x_studio_transporti') and
                    rec.x_studio_transporti and
                    rec.category_code == 'mivlineba'
                )
                if transport_applies:
                    disp = getattr(rec, 'x_studio_transport_disp', False)
                    if disp:
                        #new_lines = []
                        #for line in rec.employee_line_ids:
                            #new_lines.append((0, 0, {
                                #'employee_id': line.employee_id.id,
                                #'car_id': line.car_id.id,
                                #'km': line.km,
                                #'moto_hours': line.moto_hours,
                            #}))
                        new_mox = rec.env['moxsenebiti'].create({
                            'request_owner_id': disp.id,
                            'x_studio_moxsenebiti_to_edit': rec.id,
                            'category_id': rec.category_id.id,
                            #'start_date': rec.start_date,
                            #'end_date': rec.end_date,
                            #'mivlineba_type': rec.mivlineba_type,
                            #'stay_type': rec.stay_type,
                            #'comment': rec.comment,
                            #'employee_line_ids': new_lines,
                        })
                        new_mox._create_activity_for_user(
                            disp,
                            summary="ახალი სატრანსპორტო მოხსენება",
                            note=_("გთხოვთ იხილოთ და შეავსოთ ახალი მოხსენება (დაკავშირებული: %s)") % rec.display_name,
                        )
                    rec._notify_author_to_sign()
                else:
                    # If no approvers and no transport, notify author to sign directly
                    rec._notify_author_to_sign()

    def action_approve(self):
        self.ensure_one()

        if not self.is_current_approver or self.state != "sent":
            raise UserError(_("თქვენგან არ ელოდება დოკუმენტი დასტურს."))

        my_lines = self.approver_line_ids.filtered(lambda l: l.user_id.id == self.env.user.id and l.state == 'waiting')
        if not my_lines:
            raise UserError(_("No waiting line found for you."))

        # Determine which type of approver this is (regular or transport)
        my_type = my_lines[0].approver_type  # 'regular' or 'transport'

        # mark all my lines approved (in case duplicate user)
        my_lines.write({"state": "approved", "decision_date": fields.Datetime.now()})
        self._done_activity_for_user(self.env.user, "მოხსენება - დადასტურება")
        self.message_post(body=_("Approved by %s") % self.env.user.name)

        # --- Check if transport sub-flow applies ---
        transport_applies = (
            hasattr(self, 'x_studio_transporti') and
            self.x_studio_transporti and
            self.category_code == 'mivlineba'
        )

        if my_type == 'transport':
            # Transport approver approved — check if all transport lines done
            transport_lines = self.approver_line_ids.filtered(lambda l: l.approver_type == 'transport')
            all_transport_done = not transport_lines.filtered(lambda l: l.state != 'approved')
            if all_transport_done:
                self.transport_state = 'done'
                self.message_post(body=_("სატრანსპორტო ვიზირება დასრულდა. ხელმოწერის მოლოდინში."))
                self._notify_author_to_sign()
            # (if not all done yet — do nothing, others still pending)
        else:
            # Regular approver approved — check if all regular lines done
            regular_lines = self.approver_line_ids.filtered(lambda l: l.approver_type == 'regular')
            # Support legacy: if no approver_type set, fall back to treating all as regular
            if not regular_lines:
                regular_lines = self.approver_line_ids
            all_regular_done = not regular_lines.filtered(lambda l: l.state != 'approved')

            if all_regular_done:
                if transport_applies:
                    # Kick off transport sub-flow
                    # self.transport_state = 'pending_dispatch'
                    # self.message_post(body=_("ყველა ვიზა დადასტურდა. სატრანსპორტო Dispatcher-ის მოლოდინი."))
                    disp = getattr(self, 'x_studio_transport_disp', False)
                    if disp:
                        #new_lines = []
                        #for line in self.employee_line_ids:
                            #new_lines.append((0, 0, {
                                #'employee_id': line.employee_id.id,
                                #'car_id': line.car_id.id,
                                #'km': line.km,
                                #'moto_hours': line.moto_hours,
                            #}))
                        new_mox = self.env['moxsenebiti'].create({
                            'request_owner_id': disp.id,
                            'x_studio_moxsenebiti_to_edit': self.id,
                            'category_id': self.category_id.id,
                            #'start_date': self.start_date,
                            #'end_date': self.end_date,
                            #'mivlineba_type': self.mivlineba_type,
                            #'stay_type': self.stay_type,
                            #'comment': self.comment,
                            #'employee_line_ids': new_lines,
                        })
                        new_mox._create_activity_for_user(
                            disp,
                            summary="ახალი სატრანსპორტო მოხსენება",
                            note=_("გთხოვთ იხილოთ და შეავსოთ ახალი მოხსენება (დაკავშირებული: %s)") % self.display_name,
                        )
                    self._notify_author_to_sign()
                    self.message_post(body=_("დადასტურებულია. ტრანსპორტისთვის შეიქმნა ახალი დოკუმენტი. ხელმოწერის მოლოდინში."))
                else:
                    # Normal flow: notify author
                    self._notify_author_to_sign()
                    self.message_post(body=_("დადასტურებულია. ხელმოწერის მოლოდინში."))

    def action_reject(self):
        self.ensure_one()
        if self.state not in ("sent", "signed"):
            return
        
        can_reject = self.is_current_approver or self.is_author_user or self.is_adresati_user or self.env.user.has_group("base.group_system")
        if not can_reject:
            raise UserError(_("Only current approver, author, adresati (or admin) can reject."))
        
        if self.state == 'signed' and not (self.is_adresati_user or self.env.user.has_group("base.group_system")):
             raise UserError(_("Only adresati (or admin) can reject a signed document."))

        # cancel all, set rejected
        self.approver_line_ids.filtered(lambda l: l.state in ("pending", "waiting")).write({"state": "cancelled"})
        self.state = "rejected"
        self.message_post(body=_("უარყოფილია %s") % self.env.user.name)
        self._done_activity_for_user(self.env.user, "მოხსენება - დადასტურება")

    def action_sign(self):
        self.ensure_one()

        if self.state != "sent":
            raise UserError(_("Document is not in approval flow."))

        if not self.all_approved:
            raise UserError(_("All approvers must approve before signing."))

        if not self.author_id:
            raise UserError(_("Please set Author first."))
        if self.author_id.id != self.env.user.id:
            raise UserError(_("Only the author can sign."))

        if self.category_code != 'biul':
            if not self.word_file:
                raise UserError(_("ხელმოწერამდე აუცილებელია ფაილის მიბმა."))

        # Attempt to sign the attached Word document
        if self.word_file:
            self._sign_word_file()

        self.signed_document = True
        self.state = "signed"

        # Create Time Off for 'biul'
        if self.category_code == 'biul':
            if not (self.leave_employee_id and self.time_off_type_id and self.start_date and self.end_date):
                raise UserError(_("Insufficient data to create Time Off (Employee, Type, Dates required)."))
            
            leave_vals = {
                'holiday_status_id': self.time_off_type_id.id,
                'employee_id': self.leave_employee_id.id,
                'request_date_from': self.start_date,
                'request_date_to': self.end_date,
                'name': self.number,
                'number_of_days': self.time_off_days,
            }
            # Create as sudo (admin)
            self.env['hr.leave'].sudo().create(leave_vals)
        
        # Updated message: Signed + Waiting for Order
        self.message_post(body=_("ხელმოწერილია %s-ის მიერ. გადაწერის მოლოდინში.") % self.env.user.name)
        
        self._done_activity_for_user(self.env.user, "მოხსენება - ხელმოწერა")

        # notify adresati after sign
        self._notify_adresati()

    def action_send_to_order(self):
        self.ensure_one()
        if self.state != "signed":
            raise UserError(_("Only signed document can be sent to order."))
        if not self.adresati_id:
            raise UserError(_("Adresati is not set."))
        if self.adresati_id.id != self.env.user.id and not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only adresati (or admin) can send to order."))

        return {
            'name': _('გადაწერა'),
            'type': 'ir.actions.act_window',
            'res_model': 'moxsenebiti.send.to.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_moxsenebiti_id': self.id},
        }

    def action_finalize_send_to_order(self, approver_user_ids):
        self.ensure_one()
        self.state = "order_sent"
        
        # Set the receiver
        self.order_receiver_ids = [(6, 0, approver_user_ids)]
        # Optional: set primary legacy field for compatibility if list is not empty
        if approver_user_ids:
             self.order_receiver_id = approver_user_ids[0]

        receivers = self.env['res.users'].browse(approver_user_ids)
        names = ", ".join(receivers.mapped('name'))
        
        self.message_post(body=_("მოხდა გადაწერა %s-ის მიერ -> %s-ზე.") % (self.env.user.name, names))
        self._done_activity_for_user(self.env.user, "მოხსენება - გადაწერა")

        # Notify the receivers to prepare the order
        for user in receivers:
             self._create_activity_for_user(
                user,
                summary="მოხსენება - გადაწერა",
                note=_("გთხოვთ მოამზადოთ ბრძანება: %s") % self.display_name,
            )

    def action_prepare_order(self):
        """Called by HR Admin (order_receiver_id) to generate the Approval Request."""
        self.ensure_one()
        
        if self.generated_approval_id:
             return {
                'type': 'ir.actions.act_window',
                'res_model': 'approval.request',
                'view_mode': 'form',
                'res_id': self.generated_approval_id.id,
                'target': 'current',
            }

        # Try to use current user if they are one of the receivers, otherwise fallback
        if self.env.user.id in self.order_receiver_ids.ids:
             approver_user_id = self.env.user.id
        elif self.order_receiver_id:
             approver_user_id = self.order_receiver_id.id
        elif self.order_receiver_ids:
             approver_user_id = self.order_receiver_ids[0].id
        else:
             approver_user_id = self.env.user.id
        request = False

        # Generate Approval Request if Mivlineba and Configured
        if self.category_code == 'mivlineba' and self.category_id.approval_category_id:
            # Type mapping
            # moxsenebiti values -> approval values
            type_map = {
                'sazgvargaret': 'abroad',
                'gazificireba': 'gazification',
                'tranziti': 'transit',
                'sakhelsh': 'agreement',
                'zogadi': 'broad',
            }
            # Stay mapping
            stay_map = {
                'with_night': 'ღამისთევა',
                'without_night': 'ღამისთევის გარეშე',
            }

            # Employee Lines mapping
            lines_vals = []
            for line in self.employee_line_ids:
                lines_vals.append((0, 0, {
                    'x_studio_employee': line.employee_id.id,
                    'x_studio_vehicle': line.car_id.id,
                    'x_studio_km': line.km,
                    'x_studio_time': line.moto_hours,
                }))

            vals = {
                'name': self.number + ' - ' + (self.comment or ''),
                'request_owner_id': approver_user_id,
                'category_id': self.category_id.approval_category_id.id,
                'moxsenebiti_id': self.id,
                'date_start': fields.Datetime.to_datetime(self.start_date),
                'date_end': fields.Datetime.to_datetime(self.end_date),
                'reason': self.comment,
                # Studio Fields Mapping
                'x_studio_goal': self.comment,
                'x_studio_type': type_map.get(self.mivlineba_type),
                'x_studio_adresati': self.adresati_id.id,
                'x_studio_spendtime': stay_map.get(self.stay_type),
                'x_studio_comment1': self.number,
                'x_studio_advance_pay': self.x_studio_advance_pay,
                'x_studio_invoice': self.x_studio_invoice,
                # Lines mapping
                'table_line_ids': lines_vals,
            }
            request = self.env['approval.request'].create(vals)
            #request.action_confirm()

        # Generate Approval Request if Mivl Edit and Configured (same as mivlineba)
        elif self.category_code == 'mivledit' and self.category_id.approval_category_id:
            type_map = {
                'sazgvargaret': 'abroad',
                'gazificireba': 'gazification',
                'tranziti': 'transit',
                'sakhelsh': 'agreement',
                'zogadi': 'broad',
            }
            stay_map = {
                'with_night': 'ღამისთევა',
                'without_night': 'ღამისთევის გარეშე',
            }

            lines_vals = []
            for line in self.employee_line_ids:
                lines_vals.append((0, 0, {
                    'x_studio_employee': line.employee_id.id,
                    'x_studio_vehicle': line.car_id.id,
                    'x_studio_km': line.km,
                    'x_studio_time': line.moto_hours,
                }))

            vals = {
                'name': self.number + ' - ' + (self.comment or ''),
                'request_owner_id': approver_user_id,
                'category_id': self.category_id.approval_category_id.id,
                'moxsenebiti_id': self.id,
                'date_start': fields.Datetime.to_datetime(self.start_date),
                'date_end': fields.Datetime.to_datetime(self.end_date),
                'reason': self.comment,
                # Studio Fields Mapping
                'x_studio_goal': self.comment,
                'x_studio_type': type_map.get(self.mivlineba_type),
                'x_studio_adresati': self.adresati_id.id,
                'x_studio_spendtime': stay_map.get(self.stay_type),
                'x_studio_comment1': self.number,
                'x_studio_advance_pay': self.x_studio_advance_pay,
                'x_studio_invoice': self.x_studio_invoice,
                # Lines mapping
                'table_line_ids': lines_vals,
                'x_studio_type_selection': self.x_studio_type_selection,
            }
            request = self.env['approval.request'].create(vals)
            #request.action_confirm()

        # Generate Approval Request if Shvebuleba and Configured
        elif self.category_code == 'shvebuleba' and self.category_id.approval_category_id:
            vals = {
                'name': self.number + ' - ' + (self.comment or ''),
                'request_owner_id': approver_user_id,
                'category_id': self.category_id.approval_category_id.id,
                'moxsenebiti_id': self.id,
                'date_start': fields.Datetime.to_datetime(self.start_date),
                'date_end': fields.Datetime.to_datetime(self.end_date),
                'reason': self.comment, # Might be empty, but keeping consistency
                # Studio Fields Mapping
                'x_studio_adresati': self.adresati_id.id,
                'x_studio_time_off_type': self.time_off_type_id.id,
                'x_studio_employee_new': self.leave_employee_id.id,
                'x_studio_comment1': self.number,
                'x_studio_contract_start': self.start_date,
                'x_studio_contract_end': self.end_date,
                'x_studio_advance_pay': self.x_studio_advance_pay,
                'x_studio_invoice': self.x_studio_invoice,
            }
            request = self.env['approval.request'].create(vals)
            #request.action_confirm()

        # Generate Approval Request if Shvebucanc and Configured
        elif self.category_code == 'shvebucanc' and self.category_id.approval_category_id:
            vals = {
                'name': self.number + ' - ' + (self.comment or ''),
                'request_owner_id': approver_user_id,
                'category_id': self.category_id.approval_category_id.id,
                'moxsenebiti_id': self.id,
                'date_start': fields.Datetime.to_datetime(self.start_date),
                'date_end': fields.Datetime.to_datetime(self.end_date),
                'reason': self.comment,
                # Studio Fields Mapping
                'x_studio_adresati': self.adresati_id.id,
                'x_studio_time_off_type': self.time_off_type_id.id,
                'x_studio_employee_new': self.leave_employee_id.id,
                'x_studio_comment1': self.number,
                'x_studio_contract_start': self.start_date,
                'x_studio_contract_end': self.end_date,
                'x_studio_type_selection': self.x_studio_type_selection,
                'x_studio_time_off_id': self.x_studio_time_off_id.id,
                'x_studio_advance_pay': self.x_studio_advance_pay,
                'x_studio_invoice': self.x_studio_invoice,
            }
            request = self.env['approval.request'].create(vals)
            #request.action_confirm()

        # For Bonus (Zogadi), pop up wizard to choose the approval category
        elif self.category_code == 'Bonus':
            return {
                'name': _('ბრძანების კატეგორიის შერჩევა'),
                'type': 'ir.actions.act_window',
                'res_model': 'moxsenebiti.prepare.order',
                'view_mode': 'form',
                'target': 'new',
                'context': {'default_moxsenebiti_id': self.id},
            }
        
        if request:
            self.generated_approval_id = request.id
            
            if approver_user_id:
                request.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=approver_user_id,
                    summary=_("მოხსენება გამოგეწერათ"),
                    note=_("შეიქმნა ახალი მოთხოვნა: %s") % request.name
                )
            
            # Mark preparation task done
            self._done_activity_for_user(self.env.user, "მოხსენება - გადაწერა")
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'approval.request',
                'view_mode': 'form',
                'res_id': request.id,
                'target': 'current',
            }

    def action_open_forward_wizard(self):
        self.ensure_one()
        return {
            'name': _('გადაწერა'),
            'type': 'ir.actions.act_window',
            'res_model': 'moxsenebiti.send.to.order',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_moxsenebiti_id': self.id},
        }

    def action_open_add_approver(self):
        self.ensure_one()
        if not self.can_manage_approvers:
            raise UserError(_("ამ ეტაპზე დამდასტურებლის დამატება არ არის შესაძლებელი."))
        return {
            'name': _('დამდასტურებლის დამატება'),
            'type': 'ir.actions.act_window',
            'res_model': 'moxsenebiti.add.approver',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_moxsenebiti_id': self.id},
        }

    def action_reset_to_draft(self):
        for rec in self:
            rec.approver_line_ids.write({"state": "pending", "decision_date": False})
            rec.state = "draft"
            rec.signed_document = False
            rec.transport_state = 'none'
            self.message_post(body=_("დაბრუნდა დრაფტში."))

    def action_open_change_owner(self):
        self.ensure_one()
        return {
            'name': _('გადაწერა (ინიციატორის შეცვლა)'),
            'type': 'ir.actions.act_window',
            'res_model': 'moxsenebiti.change.owner',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_moxsenebiti_id': self.id},
        }

    def action_reinitiate(self):
        self.ensure_one()
        return {
            'name': _('დაბრუნების მიზეზი'),
            'type': 'ir.actions.act_window',
            'res_model': 'moxsenebiti.reinitiate',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_moxsenebiti_id': self.id},
        }

    # def action_open_dispatch_wizard(self):
    #     """Opens the transport dispatch wizard for x_studio_transport_disp."""
    #     self.ensure_one()
    #     if not self.can_dispatch:
    #         raise UserError(_("ამ მოქმედების შესრულება ამ ეტაპზე შეუძლებელია."))
    #     return {
    #         'name': _("ტრანსპორტის დეპარტამენტი"),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'moxsenebiti.transport.dispatch',
    #         'view_mode': 'form',
    #         'target': 'new',
    #         'context': {
    #             'default_moxsenebiti_id': self.id,
    #             'dialog_size': 'extra-large',
    #         },
    #     }


class MoxsenebitiCategory(models.Model):
    _name = "moxsenebiti.category"
    _description = "Moxsenebiti Category"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Technical code, e.g. mivlineba, shvebuleba")
    image = fields.Binary(string="Image", attachment=True)
    
    to_review_count = fields.Integer(string="To Review", compute="_compute_to_review_count")

    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sequence",
        required=True,
        ondelete="restrict",
        help="Each category has its own numbering.",
    )
    
    approval_category_id = fields.Many2one("approval.category", string="Approval Category", help="If set, an approval request will be generated when sending to order.")

    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Category code must be unique."),
    ]

    def _compute_to_review_count(self):
        for rec in self:
            # Count moxsenebiti where specific user is waiting approver
            # relying on 'is_current_approver' logic might be slow to search, so direct search is better
            # Find records where state=sent AND category=rec AND user is in waiting approver lines
            count = self.env['moxsenebiti'].search_count([
                ('category_id', '=', rec.id),
                ('state', '=', 'sent'),
                ('approver_line_ids.user_id', '=', self.env.user.id),
                ('approver_line_ids.state', '=', 'waiting'),
            ])
            rec.to_review_count = count

    def action_create_request(self):
        self.ensure_one()
        return {
            "name": _("New Request"),
            "type": "ir.actions.act_window",
            "res_model": "moxsenebiti",
            "view_mode": "form",
            "context": {"default_category_id": self.id},
        }
    
    def action_open_to_review(self):
        self.ensure_one()
        return {
            "name": _("To Review"),
            "type": "ir.actions.act_window",
            "res_model": "moxsenebiti",
            "view_mode": "list,form",
            "domain": [
                ('category_id', '=', self.id),
                ('state', '=', 'sent'),
                ('approver_line_ids.user_id', '=', self.env.user.id),
                ('approver_line_ids.state', '=', 'waiting'),
            ],
        }


class MoxsenebitiApproverLine(models.Model):
    _name = "moxsenebiti.approver.line"
    _description = "Approver Line"
    _order = "sequence, id"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="Moxsenebiti", required=True, ondelete="cascade")
    sequence = fields.Integer(string="Sequence", default=10)
    user_id = fields.Many2one("res.users", string="დამდასტურებელი", required=True)

    approver_type = fields.Selection(
        [
            ('regular', 'ჩვეულებრივი'),
            ('transport', 'სატრანსპორტო'),
        ],
        string="ვიზის ტიპი",
        default='regular',
        required=True,
    )

    state = fields.Selection(
        [
            ("pending", "მომლოდინე"),
            ("waiting", "ვიზირება"),
            ("approved", "დადასტურებული"),
            ("cancelled", "გაუქმებული"),
        ],
        string="სტატუსი",
        default="pending",
        required=True,
        tracking=True,
    )

    decision_date = fields.Datetime(string="გადაწყვეტილების თარიღი", readonly=True)

    can_be_removed = fields.Boolean(compute="_compute_can_be_removed", store=False)

    @api.depends(
        "state",
        "moxsenebiti_id.state",
        "moxsenebiti_id.signed_document",
        "moxsenebiti_id.request_owner_id",
        "moxsenebiti_id.author_id",
    )
    def _compute_can_be_removed(self):
        uid = self.env.user.id
        is_admin = self.env.user.has_group("base.group_system")
        for line in self:
            mox = line.moxsenebiti_id
            is_owner_or_author = (
                (mox.request_owner_id and mox.request_owner_id.id == uid)
                or (mox.author_id and mox.author_id.id == uid)
            )
            line.can_be_removed = (
                mox.state == "sent"
                and not mox.signed_document
                and line.state in ("pending", "waiting")
                and (is_owner_or_author or is_admin)
            )

    def action_remove_approver_line(self):
        """Called from the row X button. Removes a pending/waiting approver line."""
        for line in self:
            mox = line.moxsenebiti_id
            uid = self.env.user.id
            is_admin = self.env.user.has_group("base.group_system")
            is_owner_or_author = (
                (mox.request_owner_id and mox.request_owner_id.id == uid)
                or (mox.author_id and mox.author_id.id == uid)
            )
            if not (is_owner_or_author or is_admin):
                raise UserError(_("დამდასტურებლის წაშლა შეუძლია მხოლოდ ინიციატორს, ავტორს ან ადმინისტრატორს."))
            if mox.state != "sent" or mox.signed_document:
                raise UserError(_("ამ ეტაპზე დამდასტურებლის წაშლა არ არის შესაძლებელი."))
            if line.state not in ("pending", "waiting"):
                raise UserError(_("მხოლოდ მოლოდინში მყოფი დამდასტურებლის წაშლაა შესაძლებელი."))

            user = line.user_id
            if user:
                mox._done_activity_for_user(user, "მოხსენება - დადასტურება")

            user_name = user.name if user else _("უცნობი")
            line.unlink()
            mox.message_post(
                body=_("წაიშალა დამდასტურებელი: %s (%s-ის მიერ).") % (user_name, self.env.user.name)
            )

            if mox.all_approved:
                mox._notify_author_to_sign()


class MoxsenebitiEmployeeLine(models.Model):
    _name = "moxsenebiti.employee.line"
    _description = "Employee Line"
    _order = "id"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="Moxsenebiti", required=True, ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="თანამშრომელი")
    car_id = fields.Many2one("fleet.vehicle", string="ავტომობილი")

    wvis_norma = fields.Float(string="წვის ნორმა", compute="_compute_norms", store=True)
    moto_norma = fields.Float(string="მოტო ნორმა", compute="_compute_norms", store=True)

    km = fields.Float(string="კმ")
    moto_hours = fields.Float(string="მოტო/სთ")
    fuel_amount_km = fields.Float(string="საწვავი (კმ)", compute="_compute_fuel_amount", store=True)
    fuel_amount_moto = fields.Float(string="საწვავი (მოტო)", compute="_compute_fuel_amount", store=True)
    fuel_amount = fields.Float(string="საწვავის რაოდენობა", compute="_compute_fuel_amount", store=True)

    @api.depends("km", "moto_hours", "wvis_norma", "moto_norma")
    def _compute_fuel_amount(self):
        for rec in self:
            # Formula: (km * wvis_norma / 100) + (moto_hours * moto_norma)
            fuel_from_km = (rec.km * rec.wvis_norma) / 100.0
            fuel_from_moto = rec.moto_hours * rec.moto_norma
            
            rec.fuel_amount_km = fuel_from_km
            rec.fuel_amount_moto = fuel_from_moto
            rec.fuel_amount = fuel_from_km + fuel_from_moto

    @api.depends("car_id")
    def _compute_norms(self):
        for rec in self:
            rec.wvis_norma = 0.0
            rec.moto_norma = 0.0
            if rec.car_id:
                # User specified Studio field names:
                # One2many: x_studio_one2many_field_55n_1j0p4eqma
                # Fields on O2M line: x_studio_wvisnorma_, x_studio_wvisnomra_motosaati
                
                # Check if field exists to avoid crash if studio field missing in dev
                if hasattr(rec.car_id, "x_studio_one2many_field_55n_1j0p4eqma"):
                    lines = getattr(rec.car_id, "x_studio_one2many_field_55n_1j0p4eqma")
                    if lines:
                        # Assuming we want the latest norm? Taking the last one.
                        last_line = lines[-1]
                        if hasattr(last_line, "x_studio_wvisnorma_"):
                            rec.wvis_norma = getattr(last_line, "x_studio_wvisnorma_")
                        if hasattr(last_line, "x_studio_wvisnomra_motosaati"):
                            rec.moto_norma = getattr(last_line, "x_studio_wvisnomra_motosaati")


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    moxsenebiti_id = fields.Many2one("moxsenebiti", string="Related Moxsenebiti", readonly=True)
