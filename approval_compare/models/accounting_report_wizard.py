from odoo import models, fields, api

CANCEL_CATEGORY_ID = 26
EMPLOYEE_ACCOUNT_CODE = '1430'
DAILY_LOCAL = 30
HOTEL_LOCAL = 70
HOTEL_GAS = 120


class MissionAccountingReportWizard(models.TransientModel):
    _name = 'mission.accounting.report.wizard'
    _description = 'Mission Accounting Comparison'

    date_from = fields.Date(
        string="თარიღიდან",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="თარიღამდე",
        required=True,
        default=fields.Date.today,
    )
    show_matching = fields.Boolean(
        string="დამთხვეული ხაზების ჩვენება",
        default=False,
    )

    def action_generate(self):
        self.ensure_one()
        self.env['mission.accounting.report.line'].sudo().search(
            [('create_uid', '=', self.env.uid)]
        ).unlink()

        vals_list = _compute_lines(self.env, self)

        if not vals_list:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'ამ პერიოდში შეუსაბამობა არ მოიძებნა.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        lines = self.env['mission.accounting.report.line'].sudo().create(vals_list)

        return {
            'type': 'ir.actions.act_window',
            'name': 'ბუღალტრული შედარება  %s – %s' % (self.date_from, self.date_to),
            'res_model': 'mission.accounting.report.line',
            'view_mode': 'list',
            'domain': [('id', 'in', lines.ids)],
            'context': {
                'search_default_group_by_order': 1,
                'create': False,
            },
            'target': 'current',
        }


class MissionAccountingReportLine(models.TransientModel):
    _name = 'mission.accounting.report.line'
    _description = 'Mission Accounting Comparison Line'
    _order = 'req_date, req_name, emp_name'

    req_id       = fields.Many2one('approval.request', string="ბრძანება", ondelete='set null')
    req_name     = fields.Char(string="ბრძანება")
    req_date     = fields.Date(string="თარიღი")
    emp_name     = fields.Char(string="თანამშრომელი")
    partner_id   = fields.Many2one('res.partner', string="პარტნიორი", ondelete='set null')
    mission_type = fields.Selection([
        ('broad',        'ზოგადი'),
        ('gazification', 'გაზიფიცირება'),
        ('transit',      'ტრანზიტი'),
        ('agreement',    'სახელშეკრულებო'),
        ('abroad',       'საზღვარგარეთ'),
        ('Inside',       'Inside'),
    ], string="ტიპი")
    op_type = fields.Selection([
        ('new',    'ახალი'),
        ('edit',   'რედაქტირება'),
        ('cancel', 'გაუქმება'),
    ], string="ოპერაცია")
    days       = fields.Integer(string="დღეები")
    calculated = fields.Float(string="გამოთვლილი", digits=(16, 2))
    posted     = fields.Float(string="გატარებული", digits=(16, 2))
    diff       = fields.Float(string="სხვაობა", digits=(16, 2))

    def action_open_moves(self):
        self.ensure_one()
        moves = self.env['account.move'].sudo().search([
            ('x_studio_brdzaneba', '=', self.req_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', '!=', 'cancel'),
        ])
        return {
            'type': 'ir.actions.act_window',
            'name': 'ბუღალტრული ჩანაწერები – %s' % self.emp_name,
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', moves.ids)],
            'target': 'current',
        }


# ---------------------------------------------------------------------------
# Computation helpers
# ---------------------------------------------------------------------------

def _compute_lines(env, wizard):
    credit_acc = env['account.account'].sudo().search(
        [('code', '=', EMPLOYEE_ACCOUNT_CODE)], limit=1
    )
    credit_acc_id = credit_acc.id if credit_acc else False

    domain = [('accounting_generated', '=', True)]
    if wizard.date_from:
        domain.append(('date_end', '>=', wizard.date_from))
    if wizard.date_to:
        domain.append(('date_end', '<=', wizard.date_to))

    requests = env['approval.request'].sudo().search(domain, order='date_end, name')
    result = []

    for req in requests:
        is_cancel = (
            req.category_id.id == CANCEL_CATEGORY_ID
            and getattr(req, 'x_studio_type_selection', '') == 'cancel'
        )
        is_edit = (
            req.category_id.id == CANCEL_CATEGORY_ID
            and getattr(req, 'x_studio_type_selection', '') == 'edit'
        )
        op_type = 'cancel' if is_cancel else ('edit' if is_edit else 'new')

        for table_line in req.table_line_ids:
            emp = table_line.x_studio_employee
            if not emp:
                continue
            partner_id = emp.work_contact_id.id
            if not partner_id:
                continue

            calculated = _calc_expected(env, req, partner_id, credit_acc_id, is_cancel, is_edit)
            posted     = _get_posted_net(env, req, partner_id, credit_acc_id)
            diff       = posted - calculated

            if not wizard.show_matching and abs(diff) < 0.01:
                continue

            result.append({
                'req_id':       req.id,
                'req_name':     req.name or '',
                'req_date':     req.date_end,
                'emp_name':     emp.name or '',
                'partner_id':   partner_id,
                'mission_type': getattr(req, 'x_studio_type', False) or False,
                'op_type':      op_type,
                'days':         getattr(req, 'x_studio_dgeebi', 0) or 0,
                'calculated':   calculated,
                'posted':       posted,
                'diff':         diff,
            })

    return result


def _calc_expected(env, req, partner_id, credit_acc_id, is_cancel, is_edit):
    if is_cancel or is_edit:
        original = _get_original_credits(env, req, partner_id, credit_acc_id)
        if is_cancel:
            return -original
        days = getattr(req, 'x_studio_dgeebi', 0) or 0
        return (_formula(req, days) - original) if days > 0 else -original

    days = getattr(req, 'x_studio_dgeebi', 0) or 0
    return _formula(req, days) if days > 0 else 0.0


def _formula(req, days):
    daily = DAILY_LOCAL * days
    hotel = 0.0
    if getattr(req, 'x_studio_spendtime', False) == 'ღამისთევა':
        if getattr(req, 'x_studio_invoice', False):
            hotel = 1.0
        else:
            rate = HOTEL_GAS if getattr(req, 'x_studio_type', '') == 'gazification' else HOTEL_LOCAL
            hotel = rate * (days - 1)
    return daily + hotel


def _get_original_credits(env, req, partner_id, credit_acc_id):
    if not credit_acc_id:
        return 0.0
    try:
        past = req.moxsenebiti_id
        edit_link = getattr(past, 'x_studio_moxsenebiti_to_edit', False)
        past_req = getattr(edit_link, 'generated_approval_id', False) if edit_link else False
    except AttributeError:
        return 0.0
    if not past_req:
        return 0.0
    total = 0.0
    for move in env['account.move'].sudo().search([
        ('x_studio_brdzaneba', '=', past_req.id),
        ('partner_id', '=', partner_id),
        ('state', '!=', 'cancel'),
    ]):
        for ml in move.line_ids:
            if ml.account_id.id == credit_acc_id:
                total += ml.credit - ml.debit
    return total


def _get_posted_net(env, req, partner_id, credit_acc_id):
    if not credit_acc_id:
        return 0.0
    total = 0.0
    for move in env['account.move'].sudo().search([
        ('x_studio_brdzaneba', '=', req.id),
        ('partner_id', '=', partner_id),
        ('state', '!=', 'cancel'),
    ]):
        for ml in move.line_ids:
            if ml.account_id.id == credit_acc_id:
                total += ml.credit - ml.debit
    return total
