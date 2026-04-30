from odoo import models, fields, api

class FixAccountingDateWizard(models.TransientModel):
    _name = 'fix.accounting.date.wizard'
    _description = 'Fix Accounting Date Wizard'

    def action_fix_dates(self):
        active_ids = self._context.get('active_ids')
        pickings = self.env['stock.picking'].browse(active_ids)
        return pickings.action_fix_accounting_dates()
