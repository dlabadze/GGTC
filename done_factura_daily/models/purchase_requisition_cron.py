import logging
from datetime import timedelta
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PurchaseRequisitionCron(models.Model):
    _inherit = 'purchase.requisition'

    @api.model
    def _cron_done_factura_download(self):
        self._cron_create_done_factura_from_avansi()

    @api.model
    def _cron_create_done_factura_from_avansi(self):
        requisitions = self.search([('contract_status', '=', 'მიმდინარე')])
        _logger.info('Done Factura Daily: processing %d active requisitions', len(requisitions))
        for req in requisitions:
            avansi_payment_condition = req.payment_condition_ids.filtered(
                lambda c: c.payment_condition == 'avansi'
            )[:1]
            if not avansi_payment_condition or not req.avansi_ids:
                continue
            existing_avansi_ids = self.env['done.factura'].search([
                ('requisition_avansi_daily_id', 'in', req.avansi_ids.ids),
            ]).mapped('requisition_avansi_daily_id').ids
            new_avansis = req.avansi_ids.filtered(lambda a: a.id not in existing_avansi_ids)
            if not new_avansis:
                continue
            today = fields.Date.context_today(self)
            vals_list = []
            for avansi in new_avansis:
                agree_date = avansi.date or today
                vals = {
                    'has_avansi': 'avansi',
                    'requisition_avansi_id': avansi.id,
                    'requisition_avansi_daily_id': avansi.id,
                    'arequisition_ids': [(6, 0, [req.id])],
                    'agree_date': agree_date,
                    'transfer_date': agree_date + timedelta(days=avansi_payment_condition.days or 0),
                }
                if 'vendor_id' in req._fields and req.vendor_id:
                    vals['organization_id'] = req.vendor_id.id
                vals_list.append(vals)
            if vals_list:
                created = self.env['done.factura'].create(vals_list)
                created.sync_vendor_bills_from_requisitions()
                _logger.info(
                    'Done Factura Daily: created %d done.factura for requisition %s',
                    len(created), req.name or req.id,
                )
