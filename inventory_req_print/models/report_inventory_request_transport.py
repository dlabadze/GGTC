from odoo import models

from odoo import models, api

class ReportInventoryRequestTransport(models.AbstractModel):
    _name = 'report.inventory_req_print.report_inventory_request_transport'
    _description = 'Inventory Request Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['inventory.request'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'inventory.request',
            'docs': docs,
        }
