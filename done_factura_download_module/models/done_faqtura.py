import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context


class DoneFAQTURI(models.Model):
    _name = 'done.factura'
    _description = 'Done FAQTURI (by agree_date)'
    _rec_name = 'name'

    name = fields.Char(string='Name', compute='_compute_name', store=True, index=True)
    invoice_id = fields.Char(string='ფაქტურის ID', default='N/A')
    series = fields.Char(string='სერია', default='N/A')
    number = fields.Char(string='ფაქტურის ნომერი', default='N/A')
    registration_date = fields.Date(string='რეგისტრაციის თარიღი', default=datetime.today())
    operation_date = fields.Char(string='ოპერაციის თარიღი', help='RS ოპერაციის თარიღიდან, მაგ. იანვარი, მარტი, დეკემბერი')
    agree_date = fields.Date(string='დათანხმების თარიღი', help='RS agree_date from get_user_invoices')
    transfer_date = fields.Date(string='გადარიცხვის თარიღი', help='ნაგულისხმევად: დადასტურების თარიღი + 10 დღე')
    organization_id = fields.Many2one('res.partner', string='ორგანიზაცია')
    sa_ident_no = fields.Char(string='საიდენტიფიკაციო ნომერი')
    tanxa = fields.Float(
        string='თანხა',
        compute='_compute_tanxa',
        store=True,
        readonly=True,
    )
    vat = fields.Float(string='დღგ-ს თანხა', default=0.0)
    buyer_un_id = fields.Char(string='მყიდველსი საიდენტიფიკაციო', default='N/A')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    status = fields.Integer(string='Status', default=0)
    has_avansi = fields.Selection([
            ('avansi', 'ავანსი'),
            ('invoice_avansi', 'Invoice ავანსი'),
        ],
        string='ავანსი',
    )
    status_text = fields.Text(string='Status Text', compute='_compute_status_text')
    mdgomareoba = fields.Selection([
        ('korektirebuli', 'კორექტირებული'),
        ('gadatanili', 'გატარებული'),
        ('araferi', 'გამოწერილი')
    ], string='მდგომარეობა', default='araferi')
    waybill_type = fields.Selection([
        ('buyer', 'მყიდველის გზამკვლევი'),
        ('seller', 'გაყიდვის გზამკვლევი')
    ], string='გზამკვლევის ტიპი')
    xarjang = fields.Many2one('account.account', string='დებეტ/კრედიტის ანგარიში', help="Account to use for invoicing")
    journal_id = fields.Many2one('account.journal', string='ჟურნალი', copy=False)
    document_ids = fields.One2many('done.faqtura.document', 'done_factura_id', string='Documents')
    line_ids = fields.One2many('done.faqtura.line', 'done_factura_id', string='Lines')
    related_account_move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='done_factura_account_move_rel',
        column1='done_factura_id',
        column2='account_move_id',
        string='ინვოისები',
        copy=False,
    )
    related_account_move_count = fields.Integer(string='ინვოისები', compute='_compute_related_account_move_count')
    purchase_order_id = fields.Many2one('purchase.order', string='შეყიდვა', readonly=True, copy=False)
    purchase_order_count = fields.Integer(string='შეყიდვები', compute='_compute_purchase_order_count')
    related_purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        relation='done_factura_purchase_order_rel',
        column1='done_factura_id',
        column2='purchase_order_id',
        string='დაკავშირებული შესყიდვები',
        copy=False,
    )
    arequisition_ids = fields.Many2many(
        comodel_name='purchase.requisition',
        relation='done_factura_purchase_requisition_rel',
        column1='done_factura_id',
        column2='purchase_requisition_id',
        string='შესყიდვის მოთხოვნები',
        copy=False,
    )
    requisition_avansi_id = fields.Many2one(
        'purchase.requisition.avansi',
        string='ავანსის ხაზი',
        copy=False,
        ondelete='set null',
    )
    requisition_count = fields.Integer(
        string='მოთხოვნები',
        compute='_compute_requisition_count',
    )
    has_purchase_state = fields.Selection(
        selection=[('1', 'ხელშეკრულების გარეშე'), ('2', 'ხელშეკრულება')],
        string='PO სტატუსი',
        compute='_compute_has_purchase_state',
        store=True,
    )
    has_account_move_state = fields.Selection(
        selection=[('1', 'ინვოისის გარეშე'), ('2', 'ინვოისი')],
        string='ინვოისის სტატუსი',
        compute='_compute_has_account_move_state',
        store=True,
    )

    @api.depends('related_purchase_ids')
    def _compute_has_purchase_state(self):
        for record in self:
            record.has_purchase_state = '2' if record.related_purchase_ids else '1'

    @api.depends('series', 'number')
    def _compute_name(self):
        for record in self:
            series = (record.series or '').strip()
            number = (record.number or '').strip()
            record.name = f"{series} {number}".strip() or record.invoice_id or 'N/A'

    @api.depends(
        'line_ids.FULL_AMOUNT',
        'has_avansi',
        'arequisition_ids',
        'requisition_avansi_id',
        'requisition_avansi_id.amount',
    )
    def _compute_tanxa(self):
        for record in self:
            if record.has_avansi == 'invoice_avansi':
                base = sum(record.line_ids.mapped('FULL_AMOUNT'))
                deduct = record._sum_other_avansi_tanxa_for_shared_requisitions()
                record.tanxa = max(0.0, base - deduct)
            elif record.requisition_avansi_id:
                record.tanxa = record.requisition_avansi_id.amount or 0.0
            else:
                record.tanxa = sum(record.line_ids.mapped('FULL_AMOUNT'))

    def _sum_other_avansi_tanxa_for_shared_requisitions(self):
        self.ensure_one()
        if not self.arequisition_ids or self.has_avansi != 'invoice_avansi':
            return 0.0
        others = self.env['done.factura'].search([
            ('has_avansi', '=', 'avansi'),
            ('id', '!=', self.id),
            ('arequisition_ids', 'in', self.arequisition_ids.ids),
        ])
        return sum(others.mapped('tanxa'))

    @api.model
    def _flush_invoice_avansi_tanxa_by_requisitions(self, requisition_ids):
        if not requisition_ids:
            return
        targets = self.search([
            ('has_avansi', '=', 'invoice_avansi'),
            ('arequisition_ids', 'in', list(requisition_ids)),
        ])
        if targets:
            targets._compute_tanxa()

    @api.depends('arequisition_ids')
    def _compute_requisition_count(self):
        for record in self:
            record.requisition_count = len(record.arequisition_ids)

    @api.depends('related_account_move_ids')
    def _compute_has_account_move_state(self):
        for record in self:
            record.has_account_move_state = '2' if record.related_account_move_ids else '1'

    def _sync_related_purchases_from_organization(self):
        PurchaseOrder = self.env['purchase.order']
        for record in self:
            if not record.organization_id:
                record.write({
                    'related_purchase_ids': [(5, 0, 0)],
                    'purchase_order_id': False,
                })
                continue
            pos = PurchaseOrder.search(
                [('partner_id', '=', record.organization_id.id)],
                order='id desc',
            )
            vals = {'related_purchase_ids': [(6, 0, pos.ids)]}
            vals['purchase_order_id'] = pos[0].id if pos else False
            record.write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('transfer_date') and vals.get('agree_date'):
                ad = vals['agree_date']
                if isinstance(ad, str):
                    ad = fields.Date.from_string(ad)
                vals['transfer_date'] = ad + timedelta(days=10)
        records = super().create(vals_list)
        records._sync_related_purchases_from_organization()
        req_ids = records.mapped('arequisition_ids').ids
        if req_ids:
            self._flush_invoice_avansi_tanxa_by_requisitions(req_ids)
        return records

    def write(self, vals):
        old_req = set(self.mapped('arequisition_ids').ids)
        res = super().write(vals)
        if 'organization_id' in vals:
            self._sync_related_purchases_from_organization()
        touched_req = old_req | set(self.mapped('arequisition_ids').ids)
        if touched_req and any(
            k in vals
            for k in ('has_avansi', 'arequisition_ids', 'requisition_avansi_id', 'line_ids')
        ):
            self._flush_invoice_avansi_tanxa_by_requisitions(list(touched_req))
        return res

    def unlink(self):
        req_ids = list(set(self.mapped('arequisition_ids').ids))
        res = super().unlink()
        if req_ids:
            self.env['done.factura']._flush_invoice_avansi_tanxa_by_requisitions(req_ids)
        return res

    @api.onchange('agree_date')
    def _onchange_agree_date_transfer_date(self):
        if self.agree_date:
            self.transfer_date = self.agree_date + timedelta(days=10)

    @api.depends('related_purchase_ids')
    def _compute_purchase_order_count(self):
        for record in self:
            record.purchase_order_count = len(record.related_purchase_ids)

    @api.depends('related_account_move_ids')
    def _compute_related_account_move_count(self):
        for record in self:
            record.related_account_move_count = len(record.related_account_move_ids)

    def action_view_account_moves(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        action['name'] = 'ინვოისები'
        move_ids = self.related_account_move_ids.ids
        action['domain'] = [('id', 'in', move_ids)] if move_ids else [('id', '=', 0)]
        action['context'] = {'default_related_done_factura_ids': [(6, 0, [self.id])]}
        return action

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('purchase.purchase_rfq')
        action['name'] = 'შეყიდვები'
        po_ids = self.related_purchase_ids.ids
        action['domain'] = [('id', 'in', po_ids)] if po_ids else [('id', '=', 0)]
        action['context'] = {'default_partner_id': self.organization_id.id} if self.organization_id else {}
        return action

    def action_view_requisitions(self):
        self.ensure_one()
        req_ids = self.arequisition_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'შესყიდვის მოთხოვნები',
            'res_model': 'purchase.requisition',
            'view_mode': 'list,form',
            'domain': [('id', 'in', req_ids)] if req_ids else [('id', '=', 0)],
            'context': {},
        }

    def _get_invoice_lines_for_register_payment(self, moves):
        """Payable/receivable move lines with open residual (same rules as account.payment.register)."""
        Line = self.env['account.move.line']
        available = Line.browse()
        valid_account_types = self.env['account.payment']._get_valid_payment_account_types()
        for line in moves.line_ids:
            if line.account_type not in valid_account_types:
                continue
            if line.currency_id:
                if line.currency_id.is_zero(line.amount_residual_currency):
                    continue
            else:
                if line.company_currency_id.is_zero(line.amount_residual):
                    continue
            available |= line
        return available

    def action_pay_related_moves(self):
        """Create and post account.payment(s): amount=tanxa, date=transfer_date, memo from each linked move."""
        self.ensure_one()
        if not self.journal_id:
            raise UserError('აირჩიეთ ჟურნალი (ჟურნალი).')
        if not self.transfer_date:
            raise UserError('მიუთითეთ გადარიცხვის თარიღი (გადარიცხვის თარიღი).')

        moves = self.related_account_move_ids.filtered(
            lambda m: m.state == 'posted' and m.is_invoice(include_receipts=True)
        )
        if not moves:
            raise UserError('დაკავშირებული გატარებული ინვოისი არ არის.')
        if len(moves.company_id.root_id) > 1:
            raise UserError('ინვოისები სხვადასხვა კომპანიისაა.')
        if len(moves.partner_id) > 1:
            raise UserError('დაკავშირებულ ინვოისებს ერთი პარტნიორი უნდა ჰყავდეთ.')

        currencies = moves.mapped('currency_id')
        if len(currencies) > 1:
            raise UserError(
                'დაკავშირებულ ინვოისებს სხვადასხვა ვალუტა აქვთ; ერთი ვალუტა საჭიროა.'
            )
        pay_currency = currencies[0] if currencies and currencies[0] else moves[0].company_id.currency_id

        lines = self._get_invoice_lines_for_register_payment(moves)
        if not lines:
            raise UserError('გადასახდელი ნაშთი არ არის (ყველა ხაზი დახურულია).')
        if len(set(lines.mapped('account_type'))) > 1:
            raise UserError('ერთდროულად შეუძლებელია შემომავალი და გამავალი გადახდის ხაზების შერჩევა.')

        memo_parts = []
        for m in moves:
            label = (m.name or m.ref or '').strip()
            memo_parts.append(label or str(m.id))
        communication = ', '.join(memo_parts)

        first = moves[0]
        line0 = lines.sorted('id')[0]
        payment_type = 'inbound' if line0.balance > 0 else 'outbound'
        partner_type = 'customer' if line0.account_type == 'asset_receivable' else 'supplier'
        if payment_type == 'outbound':
            partner_bank_id = first.partner_bank_id.id
            if not partner_bank_id and first.partner_id.bank_ids:
                partner_bank_id = first.partner_id.bank_ids[:1].id
        else:
            partner_bank_id = self.journal_id.bank_account_id.id

        pml = self.journal_id._get_available_payment_method_lines(payment_type)[:1]
        if not pml:
            raise UserError('ამ ჟურნალზე არჩეული მიმართულების გადახდის მეთოდი არ არის.')

        payment_vals = {
            'date': self.transfer_date,
            'amount': self.tanxa,
            'payment_type': payment_type,
            'partner_type': partner_type,
            'memo': communication,
            'journal_id': self.journal_id.id,
            'company_id': first.company_id.id,
            'currency_id': pay_currency.id,
            'partner_id': first.partner_id.id,
            'payment_method_line_id': pml.id,
            'destination_account_id': lines[0].account_id.id,
            'write_off_line_vals': [],
        }
        if partner_bank_id:
            payment_vals['partner_bank_id'] = partner_bank_id

        to_process = [{
            'create_vals': payment_vals,
            'to_reconcile': lines,
            'batch': {'lines': lines, 'payment_values': {}},
        }]

        Register = self.env['account.payment.register']
        wizard = Register.with_context(
            active_model='account.move',
            active_ids=moves.ids,
        ).create({})
        wctx = clean_context(dict(self.env.context))
        payments = wizard.with_context(wctx)._init_payments(to_process, edit_mode=True)
        wizard.with_context(wctx)._post_payments(to_process, edit_mode=True)
        wizard.with_context(wctx)._reconcile_payments(to_process, edit_mode=True)

        if len(payments) == 1:
            return {
                'name': 'გადახდა',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'res_id': payments.id,
                'target': 'current',
                'context': {'create': False},
            }
        return {
            'name': 'გადახდა',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments.ids)],
            'target': 'current',
            'context': {'create': False},
        }

    @api.model
    def _get_purchase_orders_for_requisitions(self, requisitions):
        if not requisitions:
            return self.env['purchase.order']
        return self.env['purchase.order'].search([('requisition_id', 'in', requisitions.ids)])

    @api.model
    def _get_vendor_moves_for_purchase_orders(self, purchase_orders):
        if not purchase_orders:
            return self.env['account.move']
        Move = self.env['account.move']
        from_invoices = purchase_orders.invoice_ids.filtered(
            lambda m: m.move_type in ('in_invoice', 'in_refund')
        )
        from_lines = Move.search([
            ('move_type', 'in', ('in_invoice', 'in_refund')),
            ('invoice_line_ids.purchase_line_id.order_id', 'in', purchase_orders.ids),
        ])
        return from_invoices | from_lines

    def sync_vendor_bills_from_requisitions(self):
        """Link vendor bills for arequisition_ids → PO → account.move (idempotent)."""
        added = 0
        for record in self:
            if not record.arequisition_ids:
                continue
            pos = self._get_purchase_orders_for_requisitions(record.arequisition_ids)
            moves = self._get_vendor_moves_for_purchase_orders(pos)
            existing = set(record.related_account_move_ids.ids)
            to_link = moves.filtered(lambda m: m.id not in existing)
            if to_link:
                record.write({'related_account_move_ids': [(4, m.id) for m in to_link]})
                added += len(to_link)
        return added

    def action_sync_vendor_bills_from_requisitions(self):
        added = self.sync_vendor_bills_from_requisitions()
        if added:
            msg = 'დაკავშირდა ახალი ინვოისი: %s' % added
        else:
            msg = 'ახალი ინვოისი არ დაემატა (უკვე დაკავშირებულია ან PO/ბილლი არ არის).'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'ინვოისები მოთხოვნიდან',
                'message': msg,
                'type': 'success' if added else 'info',
                'sticky': False,
            },
        }

    def action_some(self):
        self.ensure_one()
        return True
    
    def action_reject(self):
        self.ensure_one()
        return True

    def create_invoice_or_bill(self):
        """Creates either a vendor bill or customer invoice based on the waybill type."""
        for record in self:
            if record.mdgomareoba == 'gadatanili':
                raise UserError("ფაქტურა უკვე გატარებულია!")

            move_type = 'out_invoice' if record.waybill_type == 'seller' else 'in_invoice'

            partner = record.organization_id
            if not partner and record.sa_ident_no:
                partner = self.env['res.partner'].search([('vat', 'ilike', record.sa_ident_no.strip())], limit=1)
            if not partner:
                if not record.sa_ident_no:
                    raise UserError("ორგანიზაცია ან საიდენტიფიკაციო ნომერი არ არის მითითებული.")
                partner = self.env['res.partner'].create({
                    'name': record.organization_id.name if record.organization_id else 'N/A',
                    'vat': record.sa_ident_no,
                })

            default_account = self._get_default_account(move_type)

            if not record.line_ids:
                raise UserError("ფაქტურას არ აქვს ხაზები. გთხოვთ, დაამატოთ ხაზები გაგრძელებამდე.")

            invoice_date = record.agree_date or record.registration_date
            move_vals = {
                'move_type': move_type,
                'partner_id': partner.id,
                'invoice_date': invoice_date,
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': line.product_id.id if line.product_id else False,
                        'name': line.GOODS or (line.product_id.name if line.product_id else ''),
                        'quantity': line.G_NUMBER if line.G_NUMBER > 0 else 1,
                        'price_unit': line.price_unit if line.price_unit else ((line.FULL_AMOUNT / line.G_NUMBER) if line.G_NUMBER else line.FULL_AMOUNT),
                        'tax_ids': [(6, 0, self._get_tax_ids(line.VAT_TYPE, move_type))],
                        'account_id': line.xarjang.id if line.xarjang else default_account.id,
                    }) for line in record.line_ids
                ]
            }

            try:
                move = self.env['account.move'].create(move_vals)

                try:
                    combined_invoice = self.env['combined.invoice.model'].create({
                        'get_invoice_id': f"{record.series} {record.number}",
                        'account_move_id': move.id,
                    })
                    move.write({'combined_invoice_id': combined_invoice.id})
                except KeyError:
                    pass

                record.write({
                    'mdgomareoba': 'gadatanili',
                    'related_account_move_ids': [(4, move.id)],
                })

                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Invoice/Bill',
                    'res_model': 'account.move',
                    'view_mode': 'form',
                    'res_id': move.id,
                    'target': 'current',
                }
            except Exception as e:
                raise UserError(f"შეცდომა ინვოისის/ანგარიშის შექმნისას: {str(e)}")

    @api.depends('status')
    def _compute_status_text(self):
        for record in self:
            if record.status == -1:
                record.status_text = "სტატუსი: წაშლილი"
            elif record.status == 0:
                record.status_text = "სტატუსი: შენახული"
            elif record.status == 1:
                record.status_text = "სტატუსი: გადაგზავნილი"
            elif record.status == 2:
                record.status_text = "სტატუსი: დადასტურებული"
            elif record.status == 3:
                record.status_text = "სტატუსი: კორექტირებული პირველადი"
            elif record.status == 4:
                record.status_text = "სტატუსი: მაკორექტირებელი"
            elif record.status == 5:
                record.status_text = "სტატუსი: მაკორექტირებელი გადაგზავნილი"
            elif record.status == 6:
                record.status_text = "სტატუსი: გადაგზავნილი გაუქმებული"
            elif record.status == 7:
                record.status_text = "სტატუსი: გაუქმებული"
            else:
                record.status_text = "უცნობი სტატუსი"

    @api.depends()
    def _compute_rs_acc(self):
        for record in self:
            record.rs_acc = self.env.user.rs_acc if hasattr(self.env.user, 'rs_acc') else ''

    @api.depends()
    def _compute_rs_pass(self):
        for record in self:
            record.rs_pass = self.env.user.rs_pass if hasattr(self.env.user, 'rs_pass') else ''

    @api.onchange('xarjang')
    def _onchange_xarjang(self):
        if self.xarjang:
            for line in self.line_ids:
                line.xarjang = self.xarjang

    def _get_tax_ids(self, vat_type, move_type='out_invoice'):
        tax_type = 'sale' if move_type == 'out_invoice' else 'purchase'
        if vat_type == 1:
            tax = self.env['account.tax'].search([
                ('name', '=', '0%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        elif vat_type == 0:
            tax = self.env['account.tax'].search([
                ('name', '=', '18%'),
                ('type_tax_use', '=', tax_type)
            ], limit=1)
        else:
            tax = self.env['account.tax']
        return tax.ids if tax else []

    def _get_default_account(self, move_type):
        if move_type == 'out_invoice':
            account = self.env['account.account'].search([('code', '=', '6110')], limit=1)
        else:
            account = self.env['account.account'].search([('code', '=', '7000')], limit=1)
        if not account:
            raise UserError(f"Default account not found for move type {move_type}. Please configure the accounts.")
        return account

    def action_transfer_to_budget(self):
        """For each done.faqtura.line that has budget_analytic_id and analytic_distribution,
        find matching budget.line (by budget_analytic_id + account_id from analytic_distribution)
        and increment its paim_am by the line's FULL_AMOUNT."""
        updated_lines = 0
        errors = []

        for record in self:
            for line in record.line_ids:
                if not line.budget_analytic_id or not line.analytic_distribution:
                    continue

                # Extract analytic account IDs from analytic_distribution JSON
                # Format: {"<account_id>": <percentage>, ...}
                analytic_ids = []
                for key in (line.analytic_distribution or {}).keys():
                    for aid in key.split(','):
                        aid = aid.strip()
                        if aid.isdigit():
                            analytic_ids.append(int(aid))

                if not analytic_ids:
                    continue

                budget_lines = self.env['budget.line'].search([
                    ('budget_analytic_id', '=', line.budget_analytic_id.id),
                    ('account_id', 'in', analytic_ids),
                ])

                if not budget_lines:
                    errors.append(
                        f"budget.line not found: budget={line.budget_analytic_id.name}, "
                        f"analytic_ids={analytic_ids}, done_line={line.id}"
                    )
                    continue

                for bl in budget_lines:
                    bl.paim_am = (bl.paim_am or 0.0) + (line.FULL_AMOUNT or 0.0)
                    updated_lines += 1

        if errors:
            for e in errors:
                _logger.warning(e)

        msg = f'ბიუჯეტი განახლდა: {updated_lines} ხაზი'
        if errors:
            msg += f' | {len(errors)} ხაზი ვერ მოიძებნა (იხ. ლოგი)'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'ბიუჯეტში გატარება',
                'message': msg,
                'type': 'success' if not errors else 'warning',
                'sticky': False,
            }
        }


class DoneFAQTURALine(models.Model):
    _name = 'done.faqtura.line'
    _description = 'Done FAQTURI Line'

    done_factura_id = fields.Many2one('done.factura', string='Done Factura', required=True, ondelete='cascade')
    account_move_line_id = fields.Many2one('account.move.line', string='Account Move Line', ondelete='set null')
    product_id = fields.Many2one('product.product', string='პროდუქტი')
    GOODS = fields.Char(string='პროდუქტის დასახელება')
    G_UNIT = fields.Char(string='ერთეული')
    G_NUMBER = fields.Float(string='რაოდენობა')
    FULL_AMOUNT = fields.Float(string='ჯამური ღირებულება')
    price_unit = fields.Float(string='ერთეულის ფასი')
    DRG_AMOUNT = fields.Float(string='დღგ-ს თანხა')
    AKCIS_ID = fields.Integer(string='AKCIS ID')
    VAT_TYPE = fields.Integer(string='VAT Type')
    SDRG_AMOUNT = fields.Float(string='SDRG Amount')
    xarjang = fields.Many2one('account.account', string='დებეტი|დებეტის ანგარიში')
    analytic_distribution = fields.Json(string='Analytic Distribution')
    analytic_precision = fields.Integer(
        string='Analytic Precision',
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
    )
    budget_analytic_id = fields.Many2one('budget.analytic', string='Budget Analytic')


class DoneFAQTURADocument(models.Model):
    _name = 'done.faqtura.document'
    _description = 'Done FAQTURI Document'

    done_factura_id = fields.Many2one('done.factura', string='Done Factura', required=True, ondelete='cascade')
    document_number = fields.Char(string='ზედნადების ნომერი', required=True)
    date = fields.Date(string='თარიღი', required=True)
