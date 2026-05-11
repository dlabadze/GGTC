from odoo import api, fields, models


class PurchaseRequisitionAvansi(models.Model):
    _name = 'purchase.requisition.avansi'
    _description = 'Purchase Requisition Avansi'

    requisition_id = fields.Many2one(
        'purchase.requisition',
        string='Purchase Requisition',
        required=True,
        ondelete='cascade',
    )
    amount = fields.Float(string='ავანსი', required=True)
    date = fields.Date(string='თარიღი', required=True, default=fields.Date.today)
    percentage = fields.Float(string='პროცენტი', required=True)

    @api.onchange('amount', 'requisition_id')
    def _onchange_amount_set_percentage(self):
        for rec in self:
            contract_amount = rec.requisition_id.contract_amount if 'contract_amount' in rec.requisition_id._fields else 0.0
            if contract_amount:
                rec.percentage = (rec.amount * 100.0) / contract_amount
            else:
                rec.percentage = 0.0

    @api.onchange('percentage', 'requisition_id')
    def _onchange_percentage_set_amount(self):
        for rec in self:
            contract_amount = rec.requisition_id.contract_amount if 'contract_amount' in rec.requisition_id._fields else 0.0
            if contract_amount:
                rec.amount = (contract_amount * rec.percentage) / 100.0
            else:
                rec.amount = 0.0


class PurchaseRequisitionInheritAvansi(models.Model):
    _inherit = 'purchase.requisition'

    payment_condition = fields.Selection(
        selection=[
            ('avansi', 'ავანსი'),
            ('acceptance', 'მიღება-ჩაბარება'),
            ('invoice', 'ანგარიშ-ფაქტურა'),
            ('other', 'სხვა'),
        ],
        string='გადახდის პირობები',
    )
    other_transfer_date = fields.Date(
        string='სხვა - გადარიცხვის თარიღი',
    )
    avansi_ids = fields.One2many(
        'purchase.requisition.avansi',
        'requisition_id',
        string='ავანსები',
    )
    related_account_move_ids = fields.Many2many(
        comodel_name='account.move',
        compute='_compute_related_account_move_ids',
        string='ინვოისები (vendor bills)',
        readonly=True,
    )

    @api.depends(
        'purchase_ids.invoice_ids',
        'purchase_ids.invoice_ids.payment_state',
        'purchase_ids.invoice_ids.state',
    )
    def _compute_related_account_move_ids(self):
        done_factura = self.env['done.factura']
        PurchaseOrder = self.env['purchase.order']
        for req in self:
            pos = PurchaseOrder.search([('requisition_id', '=', req.id)])
            req.related_account_move_ids = done_factura._get_vendor_moves_for_purchase_orders(pos)

    def action_create_done_factura_from_avansi(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        candidates = self.avansi_ids
        if not candidates:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'ფაქტურა',
                    'message': 'დღევანდელი თარიღით ავანსი არ არის.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        DoneFactura = self.env['done.factura']
        vals_list = []
        for avansi in candidates:
            vals = {
                'has_avansi': 'avansi',
                'requisition_avansi_id': avansi.id,
                'arequisition_ids': [(6, 0, [self.id])],
                'agree_date': today,
            }
            vendor = self.vendor_id if 'vendor_id' in self._fields else False
            if vendor:
                vals['organization_id'] = vendor.id
            vals_list.append(vals)
        created = DoneFactura.create(vals_list)
        created.sync_vendor_bills_from_requisitions()
        if len(created) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Done ფაქტურა',
                'res_model': 'done.factura',
                'view_mode': 'form',
                'res_id': created.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Done ფაქტურა',
            'res_model': 'done.factura',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }

    def action_create_done_factura_from_other(self):
        self.ensure_one()
        if self.payment_condition != 'other':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'ფაქტურა',
                    'message': 'აირჩიეთ გადახდის პირობები: სხვა.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        if not self.other_transfer_date:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'ფაქტურა',
                    'message': 'შეავსეთ სხვა - გადარიცხვის თარიღი.',
                    'type': 'warning',
                    'sticky': False,
                },
            }
        if not self.line_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'ფაქტურა',
                    'message': 'მოთხოვნაზე ხაზები არ არის.',
                    'type': 'warning',
                    'sticky': False,
                },
            }

        today = fields.Date.context_today(self)
        vals = {
            'arequisition_ids': [(6, 0, [self.id])],
            'agree_date': today,
            'transfer_date': self.other_transfer_date,
            # Intentionally not setting has_avansi.
        }
        vendor = self.vendor_id if 'vendor_id' in self._fields else False
        if vendor:
            vals['organization_id'] = vendor.id

        done_factura = self.env['done.factura'].create(vals)
        done_line_vals = []
        for req_line in self.line_ids:
            product = req_line.product_id if 'product_id' in req_line._fields else False
            qty = req_line.product_qty if 'product_qty' in req_line._fields else 0.0
            price_unit = req_line.price_unit if 'price_unit' in req_line._fields else 0.0
            full_amount = req_line.total_amount if 'total_amount' in req_line._fields else qty * price_unit

            goods_name = ''
            if 'product_description_variants' in req_line._fields and req_line.product_description_variants:
                goods_name = req_line.product_description_variants
            elif 'name' in req_line._fields and req_line.name:
                goods_name = req_line.name
            elif product:
                goods_name = product.display_name

            done_vals = {
                'done_factura_id': done_factura.id,
                'product_id': product.id if product else False,
                'GOODS': goods_name,
                'G_UNIT': req_line.product_uom_id.name if 'product_uom_id' in req_line._fields and req_line.product_uom_id else '',
                'G_NUMBER': qty,
                'FULL_AMOUNT': full_amount,
                'price_unit': price_unit,
                'DRG_AMOUNT': 0.0,
                'AKCIS_ID': 0,
                'VAT_TYPE': 0,
                'SDRG_AMOUNT': 0.0,
            }
            if 'analytic_distribution' in req_line._fields and req_line.analytic_distribution:
                done_vals['analytic_distribution'] = req_line.analytic_distribution
            if 'budget_analytic_id' in req_line._fields and req_line.budget_analytic_id:
                done_vals['budget_analytic_id'] = req_line.budget_analytic_id.id
            done_line_vals.append(done_vals)

        self.env['done.faqtura.line'].create(done_line_vals)
        done_factura.sync_vendor_bills_from_requisitions()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Done ფაქტურა',
            'res_model': 'done.factura',
            'view_mode': 'form',
            'res_id': done_factura.id,
            'target': 'current',
        }
