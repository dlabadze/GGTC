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
        candidates = self.avansi_ids.filtered(lambda a: a.date == today)
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
