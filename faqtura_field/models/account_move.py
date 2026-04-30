from odoo import models, fields,api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    get_invoice_id_helper = fields.Char(
        string='ფაქტურის ნომერი',
        # compute='_compute_get_invoice_id',
        store=True,
        readonly=False
    )
    # get_zednd_number_helper = fields.Char(
    #     string='ზედნადების ნომერი',
    #     compute='_compute_get_zednd_number',
    #     store=True,
    #     readonly=False
    # )


    def action_update_invoice_id_helper(self):
        for record in self:
            _logger.info('==============================================')
            _logger.info(f"=={record.get_invoice_id}==")
            _logger.info(f"=={record.get_invoice_id_helper}==")
            if not record.get_invoice_id_helper and record.get_invoice_id:
                _logger.info(record.get_invoice_id)
                _logger.info(record.get_invoice_id_helper)
                record.write({'get_invoice_id_helper': record.get_invoice_id})
                _logger.info(record.get_invoice_id_helper)

