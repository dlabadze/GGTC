from odoo import api, models, fields


class JournalSetup(models.Model):
    _name = 'journal.setup.effective'
    _description = 'Change Effective Date Journal Setup'
    _rec_name = 'name'

    name = fields.Char(default='Default Effective Stock Journal')
    company_id = fields.Many2one('res.company')
    account_stock_journal = fields.Many2one('account.journal', ondelete='restrict', domain=lambda self: self._get_company_domain())

    @api.model
    def _get_company_domain(self):
        return [('company_id', '=', self.env.company.id)]


