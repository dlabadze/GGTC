from odoo import models

from odoo import models, api

class SepInspecGrRep(models.AbstractModel):
    _name = 'report.inventory_req_print.sep_inspec_gr_rep'
    _description = 'September Request Group Inspection'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['september.request'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'september.request',
            'docs': docs,
        }
