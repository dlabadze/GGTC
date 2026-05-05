from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime


def georgian_date(d):
    """Convert a date/datetime object to Georgian format: 2026 წლის 1 იანვარი"""
    if not d:
        return ''
    months = {
        1: 'იანვარი', 2: 'თებერვალი', 3: 'მარტი', 4: 'აპრილი',
        5: 'მაისი', 6: 'ივნისი', 7: 'ივლისი', 8: 'აგვისტო',
        9: 'სექტემბერი', 10: 'ოქტომბერი', 11: 'ნოემბერი', 12: 'დეკემბერი',
    }
    return f'{d.year} წლის {d.day} {months[d.month]}'


def georgian_amount(amount):
    """Convert a numeric amount to Georgian words.
    e.g. 4415.30 -> 'ოთხი ათას ოთხას თხუთმეტი ლარი და ოცდაათი თეთრი'
    """
    if amount is None or amount == '':
        return ''
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return str(amount)

    lari = int(amount)
    tetri = round((amount - lari) * 100)

    ones_nom = ['', 'ერთი', 'ორი', 'სამი', 'ოთხი', 'ხუთი', 'ექვსი', 'შვიდი',
                'რვა', 'ცხრა', 'ათი', 'თერთმეტი', 'თორმეტი', 'ცამეტი',
                'თოთხმეტი', 'თხუთმეტი', 'თექვსმეტი', 'ჩვიდმეტი', 'თვრამეტი', 'ცხრამეტი']
    tens_nom = ['', 'ათი', 'ოცი', 'ოცდაათი', 'ორმოცი', 'ორმოცდაათი',
                'სამოცი', 'სამოცდაათი', 'ოთხმოცი', 'ოთხმოცდაათი']
    # modifier form used when ones follow (e.g. 23 = ოცდა+სამი, 34 = ოცდა+ათ+ოთხი)
    tens_mod = ['', 'ათდა', 'ოცდა', 'ოცდა', 'ორმოცდა', 'ორმოცდა',
                'სამოცდა', 'სამოცდა', 'ოთხმოცდა', 'ოთხმოცდა']
    # Hundreds: nominative (standalone) vs modifier (before more digits)
    h_nom = {1: 'ასი', 2: 'ორასი', 3: 'სამასი', 4: 'ოთხასი',
             5: 'ხუთასი', 6: 'ექვსასი', 7: 'შვიდასი',
             8: 'რვაასი', 9: 'ცხრაასი'}
    h_mod = {1: 'ას', 2: 'ორას', 3: 'სამას', 4: 'ოთხას',
             5: 'ხუთას', 6: 'ექვსას', 7: 'შვიდას',
             8: 'რვაას', 9: 'ცხრაას'}

    def say_below_1000(n, modifier=False):
        """modifier=True means this chunk precedes ათასი/მილიონი, so use shorter forms."""
        if n == 0:
            return ''
        parts = []
        hundreds = n // 100
        remainder = n % 100
        if hundreds:
            # Use modifier form for hundreds if there are more digits after, OR if
            # the whole chunk is a modifier (precedes ათასი/მილიონი) and has remainder
            if remainder:
                parts.append(h_mod[hundreds])
            elif modifier:
                # e.g. 400 before ათასი → ოთხას ათასი
                parts.append(h_mod[hundreds])
            else:
                parts.append(h_nom[hundreds])
        if remainder < 20:
            if remainder:
                parts.append(ones_nom[remainder])
        else:
            t = remainder // 10
            o = remainder % 10
            if o == 0:
                parts.append(tens_nom[t])
            else:
                parts.append(tens_mod[t] + ones_nom[o])
        return ' '.join(parts)

    def number_to_words(n):
        if n == 0:
            return 'ნული'
        parts = []
        millions = n // 1_000_000
        thousands = (n % 1_000_000) // 1000
        below_thousand = n % 1000
        if millions:
            if millions == 1:
                parts.append('ერთი მილიონი')
            else:
                parts.append(say_below_1000(millions, modifier=True) + ' მილიონი')
        if thousands:
            if thousands == 1:
                parts.append('ერთი ათასი')
            else:
                parts.append(say_below_1000(thousands, modifier=True) + ' ათასი')
        if below_thousand:
            parts.append(say_below_1000(below_thousand, modifier=False))
        return ' '.join(parts)

    lari_words = number_to_words(lari)
    result = f'{lari_words} ლარი'
    if tetri:
        tetri_words = number_to_words(tetri)
        result += f' და {tetri_words} თეთრი'
    return result


# ============================================================
#  PURCHASE REQUISITION — display by contract_number
# ============================================================

class PurchaseRequisitionContractNumber(models.Model):
    _inherit = 'purchase.requisition'

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec.contract_number or rec.name or ''

    @api.model
    def _name_search(self, name='', domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if name:
            domain = ['|', ('contract_number', operator, name), ('name', operator, name)] + domain
        return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)




# ============================================================
#  MAIN MODEL
# ============================================================

class Inspektireba(models.Model):
    _name = 'inspektireba'
    _description = 'ინსპექტირება'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'number'

    # ----------------------------------------------------------
    # Basic Info Fields
    # ----------------------------------------------------------
    number = fields.Char(
        string='ნომერი',
        readonly=True, copy=False, default='/', tracking=True,
    )
    name = fields.Char(
        string='სახელი',
        readonly=True, copy=False, default='/', tracking=True,
    )
    initiator_id = fields.Many2one(
        'res.users', string='ინიციატორი',
        default=lambda self: self.env.user,
        required=True, readonly=True, tracking=True,
    )
    date = fields.Date(
        string='თარიღი',
        default=fields.Date.context_today, tracking=True,
    )
    requisition_id = fields.Many2one(
        'purchase.requisition', string='ხელშეკრულება', tracking=True,
    )
    other_director_name = fields.Char(
        string='მეორე მხარის ხელმომწერი', tracking=True,
    )
    other_director_position = fields.Char(
        string='მეორე მხარის ხელმომწერის თანამდებობა', tracking=True,
        default='დირექტორი',
    )

    # ----------------------------------------------------------
    # Service Period & Lines
    # ----------------------------------------------------------
    service_date_from = fields.Date(string='მომსახურების პერიოდის დასაწყისი')
    service_date_to   = fields.Date(string='მომსახურების პერიოდის დასასრული')
    service_line_ids  = fields.One2many(
        'inspektireba.service.line',
        'inspektireba_id',
        string='სერვისები',
        copy=True, tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='ვალუტა',
        default=lambda self: self.env.company.currency_id,
    )
    total_amount = fields.Monetary(
        string='ჯამური თანხა',
        compute='_compute_total_amount', store=True, tracking=True,
    )
    custom_amount = fields.Float(
        string='თანხა',
        digits=(16, 2),
        tracking=True,
        help='ამ ველის შევსების შემთხვევაში აბზაცებში ხელშეკრულების თანხის ნაცვლად გამოყენებული იქნება აქ მითითებული თანხა.',
    )
    comment = fields.Text(string='საფუძველი', tracking=True)

    # ----------------------------------------------------------
    # Paragraph Fields (inspection report text)
    # ----------------------------------------------------------
    paragraph_1 = fields.Text(string='აბზაცი 1', tracking=True)
    paragraph_2 = fields.Text(string='აბზაცი 2', tracking=True)
    paragraph_3 = fields.Text(string='აბზაცი 3', tracking=True)

    migheba_paragraph_1 = fields.Text(string='მიღება აბზაცი 1', tracking=True)
    migheba_paragraph_2 = fields.Text(string='მიღება აბზაცი 2', tracking=True)
    migheba_paragraph_3 = fields.Text(string='მიღება აბზაცი 3', tracking=True)

    # ----------------------------------------------------------
    # Timestamp Fields
    # ----------------------------------------------------------
    date_initiated = fields.Datetime(string='ინიცირების დრო',  readonly=True, copy=False)
    date_formed    = fields.Datetime(string='ფორმირების დრო',  readonly=True, copy=False)
    date_confirmed = fields.Datetime(string='დადასტურების დრო', readonly=True, copy=False)
    date_rejected  = fields.Datetime(string='უარყოფის დრო',    readonly=True, copy=False)

    # ----------------------------------------------------------
    # Approvers
    # ----------------------------------------------------------
    @api.model
    def _default_approvers(self):
        default_approvers = self.env['inspektireba.default.approver'].search([])
        return [(0, 0, {
            'user_id':  approver.user_id.id,
            'sequence': approver.sequence,
        }) for approver in default_approvers]

    approver_line_ids = fields.One2many(
        'inspektireba.approver.line', 'inspektireba_id',
        string='დამდასტურებლები',
        copy=True, default=_default_approvers,
    )

    # ----------------------------------------------------------
    # State / Status
    # ----------------------------------------------------------
    state = fields.Selection([
        ('initiated',        'ინიცირება'),
        ('formed',           'ფორმირება'),
        ('finance_approval', 'ფინანსური დეპარტამენტის დადასტურება'),
        ('confirmed',        'დადასტურებული'),
        ('rejected',         'უარყოფილი'),
    ], string='სტატუსი', default='initiated', tracking=True, required=True,
       group_expand='_expand_states')

    @api.model
    def _expand_states(self, states, domain, order=None):
        return ['initiated', 'formed', 'finance_approval', 'confirmed', 'rejected']

    # ----------------------------------------------------------
    # Computed / Helper Flags
    # ----------------------------------------------------------
    all_approved           = fields.Boolean(compute='_compute_all_approved',        store=False)
    is_current_approver    = fields.Boolean(compute='_compute_is_current_approver', store=False)

    can_send_to_approvers  = fields.Boolean(compute='_compute_buttons', store=False)
    can_approve            = fields.Boolean(compute='_compute_buttons', store=False)
    can_reject             = fields.Boolean(compute='_compute_buttons', store=False)
    can_return_to_initiated= fields.Boolean(compute='_compute_buttons', store=False)

    can_edit_paragraphs    = fields.Boolean(compute='_compute_can_edit_paragraphs', store=False)
    is_procurement_user    = fields.Boolean(compute='_compute_is_procurement_user', store=False)
    is_finance_user        = fields.Boolean(compute='_compute_is_finance_user',     store=False)
    is_transport           = fields.Boolean(compute='_compute_is_transport',        store=False)

    # ----------------------------------------------------------
    # Related Fields
    # ----------------------------------------------------------
    vendor_id       = fields.Many2one(
        'res.partner', string='კომპანია',
        related='requisition_id.vendor_id', store=True,
    )
    days_to_confirm = fields.Integer(
        string='ინიცირებიდან დამტკიცებამდე (დღე)',
        compute='_compute_days_ranges', store=True,
    )
    days_to_migheba = fields.Integer(
        string='დამტკიცებიდან მიღება ჩაბარებამდე (დღე)',
        compute='_compute_days_ranges', store=True,
    )

    # ==========================================================
    #  ONCHANGE METHODS
    # ==========================================================

    DIRECTOR_PLACEHOLDER = '{DIRECTOR}'
    POSITION_PLACEHOLDER = '{POSITION}'

    @api.onchange('other_director_name')
    def _onchange_other_director_name(self):
        """Replace the {DIRECTOR} placeholder (or previous name) with the new value."""
        for rec in self:
            new_name = rec.other_director_name or self.DIRECTOR_PLACEHOLDER
            old_name = (rec._origin.other_director_name or '') if rec._origin else ''
            for field_name in ('migheba_paragraph_1',):
                text = rec[field_name] or ''
                if self.DIRECTOR_PLACEHOLDER in text:
                    rec[field_name] = text.replace(self.DIRECTOR_PLACEHOLDER, new_name)
                elif old_name and old_name in text:
                    rec[field_name] = text.replace(old_name, new_name)

    @api.onchange('other_director_position')
    def _onchange_other_director_position(self):
        """Replace the {POSITION} placeholder (or previous position) with the new value."""
        for rec in self:
            new_pos = rec.other_director_position or self.POSITION_PLACEHOLDER
            old_pos = (rec._origin.other_director_position or '') if rec._origin else ''
            for field_name in ('migheba_paragraph_1',):
                text = rec[field_name] or ''
                if self.POSITION_PLACEHOLDER in text:
                    rec[field_name] = text.replace(self.POSITION_PLACEHOLDER, new_pos)
                elif old_pos and old_pos in text:
                    rec[field_name] = text.replace(old_pos, new_pos)

    @api.onchange('requisition_id', 'date', 'service_date_from', 'service_date_to', 'custom_amount')
    def _onchange_requisition_for_paragraphs(self):
        for rec in self:
            # ---- populate service lines first ----
            if rec.service_date_from and rec.service_date_to and rec.requisition_id:
                domain = [
                    ('date', '>=', rec.service_date_from),
                    ('date', '<=', rec.service_date_to),
                    ('x_studio_preiskuranti.purchase_agreement_id', '=', rec.requisition_id.id),
                ]
                logs = rec.env['fleet.vehicle.log.services'].search(domain)
                line_vals = [(0, 0, {'service_log_id': log.id}) for log in logs]
                rec.service_line_ids = [(5, 0, 0)] + line_vals
            elif not rec.requisition_id:
                rec.service_line_ids = [(5, 0, 0)]

            if not rec.requisition_id:
                continue

            # ---- populate director defaults from vendor contact ----
            vendor = rec.requisition_id.vendor_id if hasattr(rec.requisition_id, 'vendor_id') else None
            if vendor and not rec.other_director_name:
                rec.other_director_name = getattr(vendor, 'gas_contact_person', '') or ''

            # ---- compute total_amount inline from fresh service lines ----
            inline_total = sum(
                line.amount for line in rec.service_line_ids if line.amount
            )

            # ---- collect shared variables ----
            vendor_name = getattr(vendor, 'name', '') if vendor else ''
            contact_person = rec.other_director_name or rec.DIRECTOR_PLACEHOLDER
            contact_position = rec.other_director_position or rec.POSITION_PLACEHOLDER

            date_str    = georgian_date(rec.date) if rec.date else ''
            req_name    = rec.requisition_id.contract_number or ''
            if rec.custom_amount:
                req_amount = rec.custom_amount
            else:
                req_amount = getattr(rec.requisition_id, 'requested_amount', '')
            req_amount_words = georgian_amount(req_amount)

            req_date_start = getattr(rec.requisition_id, 'contract_registration_date', False)
            req_date_end   = getattr(rec.requisition_id, 'date_end',   False)
            req_date_start_str = georgian_date(req_date_start) if req_date_start else ''
            req_date_end_str   = georgian_date(req_date_end)   if req_date_end   else ''

            svc_date_start_str = georgian_date(rec.service_date_from) if rec.service_date_from else req_date_start_str
            svc_date_end_str   = georgian_date(rec.service_date_to)   if rec.service_date_to   else req_date_end_str

            date_confirmed_str = georgian_date(rec.date_confirmed) if rec.date_confirmed else ''
            rec_name = rec.name if rec.name and rec.name != '/' else ''

            r_type = getattr(rec, 'x_studio_type', False) or getattr(rec.requisition_id, 'x_studio_type', False)

            # ---- Paragraph 1 (always the same) ----
            rec.paragraph_1 = (
                f'შპს „საქართველოს გაზის ტრანსპორტირების კომპანიის" '
                f'გენერალური დირექტორის 2025 წლის 07 ნოემბრის №112 ბრძანების საფუძველზე '
                f'განვახორციელეთ ინსპექტირება შპს „საქართველოს გაზის ტრანსპორტირების კომპანიასა" და '
                f'„{vendor_name}" შორის, '
                f'{req_date_start_str} გაფორმებულ №{req_name} ხელშეკრულებაზე.'
            )

            # ---- მიღება Paragraph 1 (always the same) ----
            rec.migheba_paragraph_1 = (
                f'ჩვენ ქვემოთ ხელის მომწერნი, ერთის მხრივ შპს „საქართველოს გაზის ტრანსპორტირების კომპანია", '
                f'მისი გენერალური დირექტორის მოადგილის ირაკლი კანდელაკის სახით '
                f'და მეორეს მხრივ „{vendor_name}", '
                f'მისი {contact_position}ს {contact_person} სახით, წინამდებარე აქტზე ხელმოწერით ვადასტურებთ, რომ:\n'
            )

            # ---- მიღება Paragraph 3 (default, may be overridden below) ----
            rec.migheba_paragraph_3 = (
                'ხელშეკრულებით გათვალისწინებული ყველა ვალდებულება, რომელიც მხარეებს გააჩნდათ, '
                'წინამდებარე მიღება-ჩაბარების აქტის გაფორმების შემდეგ რჩება ძალაში;\n'
                'წინამდებარე აქტი დასტურდება მხარეთა ხელმოწერით.'
            )

            # ---- Type-specific paragraphs ----
            if str(r_type) == 'საქონელი':
                rec.paragraph_2 = (
                    f'აღნიშნული ხელშეკრულების საფუძველზე „მიმწოდებლის" მიერ „შემსყიდველისთვის" '
                    f'{req_date_start_str} მიწოდებულ იქნა ხელშეკრულებით გათვალისწინებული საქონელი. '
                    f'რომლის ღირებულებამ შეადგინა {req_amount} ({req_amount_words}) ლარი საქართველოს კანონმდებლობით '
                    f'გათვალისწინებული ყველა გადასახადისა და გადასახდელის ჩათვლით.'
                )
                rec.paragraph_3 = (
                    '1. მოწოდებული საქონელი შეესაბამება „ხელშეკრულების" პირობებს;\n'
                    '2. „მიმწოდებელმა" აღნიშნული ხელშეკრულებით დაკისრებული ვალდებულება '
                    'განახორციელა ხელშეკრულებით გათვალისწინებული ვადების დაცვით;'
                )
                rec.migheba_paragraph_2 = (
                    f'„მიმწოდებელმა" {req_date_end_str} მიაწოდა, ხოლო „შემსყიდველმა" '
                    f'თავისი ინსპექტირების ჯგუფის {date_confirmed_str} №{rec_name} დასკვნის საფუძველზე '
                    f'მიიღო მხარეთა შორის {req_date_start_str} გაფორმებული №{req_name} '
                    f'ხელშეკრულებით გათვალისწინებული საქონელი/საქონლის ნაწილი, '
                    f'რომლის ღირებულებამ შეადგინა {req_amount} ({req_amount_words}) ლარი;'
                )

            elif str(r_type) == 'მომსახურება':
                rec.paragraph_2 = (
                    f'აღნიშნული ხელშეკრულების საფუძველზე „მიმწოდებლის" მიერ „შემსყიდველისთვის" '
                    f'{req_date_start_str} მდგომარეობით გაწეულ იქნა ხელშეკრულებით გათვალისწინებული '
                    f'მომსახურება, რომლის ღირებულებამ შეადგინა {req_amount} ({req_amount_words}) ლარი საქართველოს '
                    f'კანონმდებლობით გათვალისწინებული ყველა გადასახადისა და გადასახდელის ჩათვლით.'
                )
                rec.paragraph_3 = (
                    '1. გაწეული მომსახურება შეესაბამება „ხელშეკრულების" პირობებს;\n'
                    '2. „მიმწოდებელმა" აღნიშნული ხელშეკრულებით დაკისრებული ვალდებულება '
                    'განახორციელა ხელშეკრულებით გათვალისწინებული ვადების დაცვით;'
                )
                rec.migheba_paragraph_2 = (
                    f'„მიმწოდებელმა" {req_date_end_str} მდგომარეობით გაუწია, ხოლო „შემსყიდველმა" '
                    f'თავისი ინსპექტირების ჯგუფის {date_confirmed_str} №{rec_name} დასკვნის საფუძველზე '
                    f'მიიღო მხარეთა შორის {req_date_start_str} გაფორმებული №{req_name} '
                    f'ხელშეკრულების (შემდგომში - „ხელშეკრულება") თანახმად მომსახურება, '
                    f'რომლის ღირებულებამ შეადგინა {req_amount} ({req_amount_words}) ლარი;'
                )

            elif str(r_type) == 'საწვავი':
                rec.paragraph_2 = (
                    f'აღნიშნული ხელშეკრულების საფუძველზე {req_date_start_str}-დან '
                    f'{req_date_end_str}-ის ჩათვლით, ბენზინგასამართი სადგურებიდან მოწოდებულ იქნა '
                    f'პრემიუმის მარკის ბენზინის ტიპის საწვავი (X) X ლიტრის ოდენობით, '
                    f'როგორც აგაი, ისე საბარათე სისტემით, '
                    f'რომლის საერთო ღირებულება შეადგენს {req_amount} ({req_amount_words}) ლარს.'
                )
                rec.paragraph_3 = (
                    '1. მოწოდებული ბენზინის საწვავი (Efix Euro Premium) შეესაბამება '
                    ' ხელშეკრულებით გათვალისწინებულ საქონელს.\n'
                    '2. „მიმწოდებელმა" ხელშეკრულებით ნაკისრი ვალდებულება შეასრულა '
                    'ზემოაღნიშნული ხელშეკრულებით მითითებული ვადების დაცვით.'
                )
                rec.migheba_paragraph_2 = (
                    f'{req_date_start_str}-დან {req_date_end_str}-ის ჩათვლით '
                    f'„მიმწოდებელმა" ჩააბარა, ხოლო „შემსყიდველმა" '
                    f'თავისი ინსპექტირების ჯგუფის {date_confirmed_str} №{rec_name} დასკვნის საფუძველზე '
                    f'მიიღო {req_date_start_str} №{req_name} გაფორმებული ხელშეკრულებით '
                    f'გათვალისწინებული პრემიუმის მარკის ბენზინის ტიპის საწვავი (X) X ლიტრის '
                    f'ოდენობით, რომლის ღირებულებამ შეადგინა {req_amount} ({req_amount_words}) ლარი.'
                )
                rec.migheba_paragraph_3 = 'აქტი სწორია რაც მხარეების მიერ დამოწმებულია ელექტრონულად:'

            elif str(r_type) == 'ტრანსპორტი':
                total_amount_words = georgian_amount(inline_total)
                rec.migheba_paragraph_1 = (
                    f'ჩვენ ქვემოთ ხელის მომწერნი, ერთის მხრივ შპს „საქართველოს გაზის ტრანსპორტირების კომპანიის" '
                    f'გენერალური დირექტორის მოადგილე ირაკლი კანდელაკი და მეორეს მხრივ „{vendor_name}" '
                    f'{contact_position} {contact_person} ვადასტურებთ რომ'
                )
                rec.paragraph_2 = (
                    f'აღნიშნული ხელშეკრულების საფუძველზე {svc_date_start_str}-დან '
                    f'{svc_date_end_str}-ის ჩათვლით მოწოდებული საქონლის ან/და მომსახურების '
                    f'ღირებულება შეადგენს {inline_total} ({total_amount_words}) ლარს, '
                    f'საქართველოს კანონმდებლობით გათვალისწინებული გადასახადების ჩათვლით.'
                )
                rec.paragraph_3 = (
                    '1. „მიმწოდებელმა" შეასრულა ხელშეკრულებით გათვალისწინებული ვალდებულება, '
                    'საქონელი ან/და მომსახურება მიწოდებულ იქნა ხელშეკრულებით გათვალისწინებული ვადის დაცვით.\n'
                    '2. მოწოდებული საქონელი ან/და მომსახურება შეესაბამება '
                    'ზემოაღნიშნული ხელშეკრულებით გათვალისწინებულ პირობებს.'
                )
                rec.migheba_paragraph_2 = (
                    f'{svc_date_start_str}-დან {svc_date_end_str}-ის ჩათვლით „მომწოდებელმა" ჩააბარა, '
                    f'ხოლო „შემსყიდველმა" მიიღო {req_date_start_str} გაფორმებული №{req_name} '
                    f'ხელშეკრულებით გათვალისწინებული საქონელი ან/და მომსახურება, '
                    f'ღირებულებით {inline_total} ({total_amount_words}) ლარი.'
                )
                rec.migheba_paragraph_3 = (
                    f'ხელშეკრულების ღირებულება შეადგენს {req_amount} ({req_amount_words}) ლარს.\n'
                    f'ნაზარდი ჯამით შესრულებულია თანხა (თანხა სიტყვიერად) ლარი\n\n'
                    f'აქტი სწორია რაც მხარეების მიერ დამოწმებულია ელექტრონულად:'
                )

            elif str(r_type) == 'სხვა':
                rec.paragraph_2 = (
                    f'აღნიშნული ხელშეკრულების საფუძველზე „მიმწოდებლის" მიერ „შემსყიდველისთვის" '
                    f'{req_date_start_str} მდგომარეობით შესრულებულ იქნა'
                )
                rec.paragraph_3 = (
                    'შპს „საქართველოს გაზის ტრანსპორტირების კომპანიის" ინსპექტირების ჯგუფის '
                    'მიერ განხორციელებული ინსპექტირების შედეგად\n'
                    'დავასკვენით:\n'
                    '1. შესრულებული სამუშაოები შეესაბამება ხელშეკრულების პირობებს;\n'
                    '2. „მიმწოდებელმა" აღნიშნული ხელშეკრულებით დაკისრებული ვალდებულება '
                    'განახორციელა ხელშეკრულებით გათვალისწინებული ვადების დაცვით;\n'
                    '3. „მიმწოდებლისთვის" გადახდილი\n\n'
                    'წინამდებარე ინსპექტირების ჯგუფის დასკვნაზე ხელისმომწერნი ვადასტურებთ, '
                    'რომ „მიმწოდებლის" მიმართ სრულად ვაკმაყოფილებთ „სახელმწიფო შესყიდვების '
                    'შესახებ" საქართველოს კანონის მე–8 მუხლით დადგენილ, ინტერესთა კონფლიქტის '
                    'თავიდან აცილების პირობებსა და წესებს.'
                )
                rec.migheba_paragraph_2 = ''
                rec.migheba_paragraph_3 = 'წინამდებარე აქტი დასტურდება მხარეთა ხელმოწერით.'

            else:
                # Fallback / unknown type
                rec.paragraph_2 = (
                    f'აღნიშნული ხელშეკრულების საფუძველზე „მიმწოდებლის" მიერ „შემსყიდველისთვის" '
                    f'{req_date_start_str} მიწოდებულ იქნა ხელშეკრულებით გათვალისწინებული '
                    f'[საქონელი/მომსახურება]. რომლის ღირებულებამ შეადგინა {req_amount} ({req_amount_words}) ლარი '
                    f'საქართველოს კანონმდებლობით გათვალისწინებული ყველა გადასახადისა და '
                    f'გადასახდელის ჩათვლით.'
                )
                rec.paragraph_3 = (
                    '1. [მოწოდებული საქონელი / გაწეული მომსახურება] შეესაბამება „ხელშეკრულების" პირობებს;\n'
                    '2. „მიმწოდებელმა" აღნიშნული ხელშეკრულებით დაკისრებული ვალდებულება '
                    'განახორციელა ხელშეკრულებით გათვალისწინებული ვადების დაცვით;'
                )
                rec.migheba_paragraph_2 = (
                    f'1. „მიმწოდებელმა" {req_date_end_str} მიაწოდა/გაუწია, ხოლო „შემსყიდველმა" '
                    f'თავისი ინსპექტირების ჯგუფის {date_confirmed_str} №{rec_name} დასკვნის საფუძველზე '
                    f'მიიღო მხარეთა შორის {req_date_start_str} №{req_name} გაფორმებული '
                    f'ხელშეკრულებით გათვალისწინებული [საქონელი/მომსახურება], '
                    f'რომლის ღირებულებამ შეადგინა {req_amount} ({req_amount_words}) ლარი;'
                )

    # ==========================================================
    #  COMPUTE METHODS
    # ==========================================================

    @api.depends('service_line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            amounts = rec.service_line_ids.mapped('amount')
            rec.total_amount = sum(amt for amt in amounts if amt)

    def _compute_is_procurement_user(self):
        uid = self.env.user.id
        proc_users = self.env['inspektireba.procurement.user'].search([]).mapped('user_id.id')
        for rec in self:
            rec.is_procurement_user = uid in proc_users

    def _compute_is_finance_user(self):
        uid = self.env.user.id
        fin_users = self.env['inspektireba.finance.user'].search([]).mapped('user_id.id')
        for rec in self:
            rec.is_finance_user = uid in fin_users

    def _compute_is_transport(self):
        for rec in self:
            r_type = getattr(rec, 'x_studio_type', False) or getattr(rec.requisition_id, 'x_studio_type', False)
            rec.is_transport = str(r_type) == 'ტრანსპორტი'

    @api.depends('date_initiated', 'date_confirmed', 'date')
    def _compute_days_ranges(self):
        for rec in self:
            if rec.date_initiated and rec.date_confirmed:
                delta = rec.date_confirmed - rec.date_initiated
                rec.days_to_confirm = delta.days
            else:
                rec.days_to_confirm = 0

            if rec.date_confirmed and rec.date:
                d_conf = rec.date_confirmed.date()
                delta2 = rec.date - d_conf
                rec.days_to_migheba = delta2.days
            else:
                rec.days_to_migheba = 0

    @api.depends('state', 'approver_line_ids.user_id')
    def _compute_can_edit_paragraphs(self):
        uid = self.env.user.id
        for rec in self:
            is_approver = uid in rec.approver_line_ids.mapped('user_id.id')
            rec.can_edit_paragraphs = (
                rec.state == 'initiated'
                or (rec.state == 'formed' and is_approver)
            )

    @api.depends('approver_line_ids.state')
    def _compute_all_approved(self):
        for rec in self:
            if not rec.approver_line_ids:
                rec.all_approved = True
            else:
                rec.all_approved = not rec.approver_line_ids.filtered(lambda l: l.state != 'approved')

    @api.depends('approver_line_ids.state', 'approver_line_ids.user_id')
    def _compute_is_current_approver(self):
        uid = self.env.user.id
        for rec in self:
            waiting_ids = rec.approver_line_ids.filtered(lambda l: l.state == 'waiting').mapped('user_id.id')
            rec.is_current_approver = uid in waiting_ids

    @api.depends('state', 'is_current_approver', 'initiator_id', 'is_procurement_user', 'is_finance_user')
    def _compute_buttons(self):
        for rec in self:
            rec.can_send_to_approvers  = rec.state == 'initiated'
            rec.can_approve = (
                (rec.state == 'formed'           and rec.is_current_approver)
                or (rec.state == 'finance_approval' and rec.is_finance_user)
            )
            rec.can_reject = (
                (rec.state in ('initiated', 'formed', 'finance_approval')
                 and (rec.is_current_approver
                      or rec.initiator_id.id == self.env.user.id
                      or rec.is_finance_user))
                or (rec.state == 'confirmed' and rec.is_procurement_user)
            )
            rec.can_return_to_initiated = rec.can_reject

    # ==========================================================
    #  CRUD OVERRIDES
    # ==========================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', '/') == '/':
                vals['number'] = self.env['ir.sequence'].next_by_code('inspektireba.sequence') or '/'
            if vals.get('name', '/') == '/':
                vals['name'] = vals.get('number') or '/'
            if not vals.get('date_initiated'):
                vals['date_initiated'] = fields.Datetime.now()
        return super().create(vals_list)

    def write(self, vals):
        paragraph_fields = [
            'paragraph_1', 'paragraph_2', 'paragraph_3',
            'migheba_paragraph_1', 'migheba_paragraph_2', 'migheba_paragraph_3',
        ]
        records_to_reset = self.env['inspektireba']

        if any(f in vals for f in paragraph_fields):
            for rec in self:
                if rec.state == 'formed':
                    changed = any(
                        f in vals and vals[f] != getattr(rec, f)
                        for f in paragraph_fields
                    )
                    if changed:
                        records_to_reset |= rec

        res = super().write(vals)

        for rec in records_to_reset:
            approved_lines = rec.approver_line_ids.filtered(lambda l: l.state == 'approved')
            if approved_lines:
                approved_lines.write({'state': 'waiting', 'decision_date': False})
                rec.message_post(body=_(
                    'ტექსტის ცვლილების გამო, უკვე დადასტურებული შეთანხმებები განულდა. '
                    'შეტყობინებები თავიდან გაიგზავნა ყველა დამდასტურებელთან.'
                ))
                for line in approved_lines:
                    if line.user_id:
                        rec._create_activity_for_user(
                            line.user_id,
                            summary='ინსპექტირება - დადასტურება (განახლებული)',
                            note=_('ტექსტი დაკორექტირდა. გთხოვთ ხელახლა დაადასტუროთ ინსპექტირება: %s') % rec.display_name,
                        )
        return res

    # ==========================================================
    #  ACTIVITY HELPERS
    # ==========================================================

    def _create_activity_for_user(self, user, summary, note=None):
        self.ensure_one()
        if not user:
            return
        at = self.env.ref('mail.mail_activity_data_todo')
        existing = self.env['mail.activity'].search_count([
            ('res_model',        '=', self._name),
            ('res_id',           '=', self.id),
            ('user_id',          '=', user.id),
            ('activity_type_id', '=', at.id),
            ('summary',          '=', summary),
        ])
        if existing:
            return
        self.activity_schedule(
            activity_type_id=at.id,
            user_id=user.id,
            summary=summary,
            note=note or '',
            date_deadline=fields.Date.today(),
        )

    def _done_activity_for_user(self, user, summary):
        self.ensure_one()
        if not user:
            return
        at = self.env.ref('mail.mail_activity_data_todo')
        acts = self.activity_ids.filtered(
            lambda a: a.user_id.id == user.id
            and a.activity_type_id.id == at.id
            and a.summary == summary
        )
        if acts:
            acts.action_feedback(_('Done'))

    def _notify_approvers(self):
        self.ensure_one()
        waiting_lines = self.approver_line_ids.filtered(lambda l: l.state == 'waiting')
        for line in waiting_lines:
            if line.user_id:
                self._create_activity_for_user(
                    line.user_id,
                    summary='ინსპექტირება - დადასტურება',
                    note=_('გთხოვთ დაადასტუროთ ინსპექტირება: %s') % self.display_name,
                )

    def _notify_procurement(self):
        self.ensure_one()
        proc_users = self.env['inspektireba.procurement.user'].search([])
        for pu in proc_users:
            if pu.user_id:
                self._create_activity_for_user(
                    pu.user_id,
                    summary='ინსპექტირება - დადასტურებულია',
                    note=_('ინსპექტირება დადასტურდა და გადმოგზავნილია შესყიდვების დეპარტამენტში: %s') % self.display_name,
                )

    def _notify_finance(self):
        self.ensure_one()
        fin_users = self.env['inspektireba.finance.user'].search([])
        for fu in fin_users:
            if fu.user_id:
                self._create_activity_for_user(
                    fu.user_id,
                    summary='ინსპექტირება - ფინანსური დადასტურება',
                    note=_('ინსპექტირება დადასტურებულია წევრების მიერ. გთხოვთ დაადასტუროთ: %s') % self.display_name,
                )

    # ==========================================================
    #  ACTION METHODS
    # ==========================================================

    def action_send_to_approvers(self):
        for rec in self:
            if rec.state != 'initiated':
                continue
            if not rec.approver_line_ids:
                rec.state = 'finance_approval'
                rec.message_post(body=_(
                    'გადაგზავნილია ფინანსურ დეპარტამენტში, '
                    'რადგან არ არის მითითებული სხვა დამდასტურებლები.'
                ))
                rec._notify_finance()
            else:
                rec.approver_line_ids.write({'state': 'waiting', 'decision_date': False})
                rec.state = 'formed'
                rec.date_formed = fields.Datetime.now()
                rec.message_post(body=_('გაგზავნილია დასადასტურებლად.'))
                rec._notify_approvers()

    def action_approve(self):
        self.ensure_one()
        if self.state == 'formed':
            if not self.is_current_approver:
                raise UserError(_('თქვენგან არ ელოდება დოკუმენტი დასტურს.'))

            my_lines = self.approver_line_ids.filtered(
                lambda l: l.user_id.id == self.env.user.id and l.state == 'waiting'
            )
            if not my_lines:
                raise UserError(_('No waiting line found for you.'))

            my_lines.write({'state': 'approved', 'decision_date': fields.Datetime.now()})
            self._done_activity_for_user(self.env.user, 'ინსპექტირება - დადასტურება')
            self.message_post(body=_('Approval from %s') % self.env.user.name)

            if self.all_approved:
                self.state = 'finance_approval'
                self.message_post(body=_(
                    'დადასტურებულია ყველა ინსპექტირების წევრის მიერ. '
                    'გადაგზავნილია ფინანსურ დეპარტამენტში.'
                ))
                self._notify_finance()

        elif self.state == 'finance_approval':
            if not self.is_finance_user:
                raise UserError(_('თქვენ არ გაქვთ ფინანსური დეპარტამენტის დადასტურების უფლება.'))
            self.state = 'confirmed'
            self.date_confirmed = fields.Datetime.now()
            self._done_activity_for_user(self.env.user, 'ინსპექტირება - ფინანსური დადასტურება')
            self.message_post(body=_('დადასტურებულია ფინანსური დეპარტამენტის მიერ.'))
            self._notify_procurement()
        else:
            raise UserError(_('არასწორი სტატუსი დადასტურებისთვის.'))

    def action_reject(self):
        self.ensure_one()
        if self.state not in ('initiated', 'formed', 'finance_approval', 'confirmed'):
            return
        can_reject = (
            self.is_current_approver
            or self.initiator_id.id == self.env.user.id
            or self.env.user.has_group('base.group_system')
            or self.is_procurement_user
            or self.is_finance_user
        )
        if not can_reject:
            raise UserError(_('Only current approver, initiator, procurement or finance user can reject.'))

        self.approver_line_ids.filtered(
            lambda l: l.state in ('pending', 'waiting')
        ).write({'state': 'cancelled'})
        self.state = 'rejected'
        self.date_rejected = fields.Datetime.now()
        self.message_post(body=_('უარყოფილია %s') % self.env.user.name)
        self._done_activity_for_user(self.env.user, 'ინსპექტირება - დადასტურება')
        self._done_activity_for_user(self.env.user, 'ინსპექტირება - ფინანსური დადასტურება')

    def action_return_to_initiated(self):
        self.ensure_one()
        if self.state not in ('formed', 'confirmed', 'rejected', 'finance_approval'):
            return
        can_return = (
            self.is_current_approver
            or self.initiator_id.id == self.env.user.id
            or self.env.user.has_group('base.group_system')
            or self.is_procurement_user
            or self.is_finance_user
        )
        if not can_return:
            raise UserError(_('Only current approver, initiator, procurement or finance user can return to initiation.'))

        self.approver_line_ids.write({'state': 'pending', 'decision_date': False})
        for act in self.activity_ids:
            act.action_feedback(_('დაბრუნებულია ინიცირებაში'))

        self.state = 'initiated'
        self.date_formed    = False
        self.date_confirmed = False
        self.date_rejected  = False
        self.message_post(body=_('დაბრუნებულია ინიცირებაში შესასწორებლად %s-ს მიერ.') % self.env.user.name)


# ============================================================
#  APPROVER LINE
# ============================================================

class InspektirebaApproverLine(models.Model):
    _name = 'inspektireba.approver.line'
    _description = 'Inspektireba Approver Line'
    _order = 'sequence, id'

    inspektireba_id = fields.Many2one(
        'inspektireba', string='Inspektireba',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    user_id  = fields.Many2one('res.users', string='დამდასტურებელი', required=True)

    state = fields.Selection([
        ('pending',    'დრაფტი'),
        ('waiting',    'მომლოდინე'),
        ('approved',   'დადასტურებული'),
        ('cancelled',  'უარყოფილი'),
    ], string='სტატუსი', default='pending', required=True, tracking=True)

    decision_date = fields.Datetime(string='გადაწყვეტილების დრო', readonly=True)


# ============================================================
#  DEFAULT APPROVER
# ============================================================

class InspektirebaDefaultApprover(models.Model):
    _name = 'inspektireba.default.approver'
    _description = 'Default Approvers for Inspektireba'
    _order = 'sequence, id'

    sequence = fields.Integer(string='მიმდევრობა', default=10)
    user_id  = fields.Many2one('res.users', string='დამდასტურებელი', required=True)


# ============================================================
#  PROCUREMENT USERS
# ============================================================

class InspektirebaProcurementUser(models.Model):
    _name = 'inspektireba.procurement.user'
    _description = 'Procurement Users for Inspektireba'

    user_id = fields.Many2one('res.users', string='მომხმარებელი', required=True)


# ============================================================
#  FINANCE USERS
# ============================================================

class InspektirebaFinanceUser(models.Model):
    _name = 'inspektireba.finance.user'
    _description = 'Finance Users for Inspektireba'

    user_id = fields.Many2one('res.users', string='მომხმარებელი (ფინანსები)', required=True)


# ============================================================
#  ATTACHMENT MIRROR — copy files from inspektireba to agreement
# ============================================================

class IrAttachmentMirrorToAgreement(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for att in attachments:
            if att.res_model != 'inspektireba' or not att.res_id:
                continue
            if self.env.context.get('inspektireba_mirror_skip'):
                continue
            inspektireba = self.env['inspektireba'].browse(att.res_id).exists()
            if not inspektireba or not inspektireba.requisition_id:
                continue
            agreement = inspektireba.requisition_id
            already = self.search_count([
                ('res_model', '=', 'purchase.requisition'),
                ('res_id', '=', agreement.id),
                ('name', '=', att.name),
                ('file_size', '=', att.file_size),
                ('checksum', '=', att.checksum),
            ])
            if already:
                continue
            att.with_context(inspektireba_mirror_skip=True).copy({
                'res_model': 'purchase.requisition',
                'res_id': agreement.id,
                'res_field': False,
            })
            agreement.message_post(body=_(
                'ფაილი დაერთო ინსპექტირებიდან %s: %s'
            ) % (inspektireba.display_name, att.name))
        return attachments


# ============================================================
#  SERVICE LINE
# ============================================================

class InspektirebaServiceLine(models.Model):
    _name = 'inspektireba.service.line'
    _description = 'სერვისები'

    inspektireba_id = fields.Many2one(
        'inspektireba', string='ინსპექტირება', ondelete='cascade',
    )
    service_log_id = fields.Many2one(
        'fleet.vehicle.log.services', string='სერვისი', required=True,
    )

    # Related (read-only) fields pulled from the service log
    date        = fields.Date(    related='service_log_id.date',        string='თარიღი',    readonly=True)
    vehicle_id  = fields.Many2one(related='service_log_id.vehicle_id',  string='ავტომობილი', readonly=True)
    description = fields.Char(    related='service_log_id.description', string='აღწერა',    readonly=True)
    currency_id = fields.Many2one(related='service_log_id.currency_id', string='ვალუტა',    readonly=True)
    amount      = fields.Monetary(related='service_log_id.amount',      string='თანხა',     readonly=True)

    def action_open_service_log(self):
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'name':      'სერვისი',
            'res_model': 'fleet.vehicle.log.services',
            'res_id':    self.service_log_id.id,
            'view_mode': 'form',
            'target':    'current',
        }
