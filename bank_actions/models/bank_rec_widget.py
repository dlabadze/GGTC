from odoo import models
import logging

_logger = logging.getLogger(__name__)

DEBUG_MODE = False


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'
    
    def _lines_prepare_auto_balance_line(self):
        existing_line = self.line_ids.filtered(lambda x: x.flag in ('auto_balance', 'manual'))
        existing_label = existing_line[0].name if existing_line and existing_line[0].name else None
        
        result = super()._lines_prepare_auto_balance_line()
        
        original_name = result.get('name', '')

        
        if existing_label and not existing_label.startswith('Open balance'):
            result['name'] = existing_label
            if DEBUG_MODE:
                _logger.info("Preserved existing label: '%s'", existing_label)
        elif original_name and original_name.startswith('Open balance') and self.st_line_id.payment_ref:
            result['name'] = self.st_line_id.payment_ref
            if DEBUG_MODE:
                _logger.info("Using payment_ref as label: '%s'", self.st_line_id.payment_ref)
        
        preserve_account_id = self.env.context.get('preserve_account_id')
        if preserve_account_id:
            result['account_id'] = preserve_account_id
        
        return result
