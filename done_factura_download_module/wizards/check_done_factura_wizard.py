from odoo import fields, models, api
from odoo.exceptions import UserError


class DoneFacturaCheckWizard(models.TransientModel):
    _name = 'done.factura.check.wizard'
    _description = 'Check done factura by period'

    date1 = fields.Date(string='საწყისი თარიღი', required=True, default=fields.Date.today)
    date2 = fields.Date(string='საბოლოო თარიღი', required=True, default=fields.Date.today)

    @api.constrains('date1', 'date2')
    def _check_dates(self):
        for rec in self:
            if rec.date1 and rec.date2 and rec.date2 < rec.date1:
                raise UserError('საბოლოო თარიღი არ უნდა იყოს საწყის თარიღზე ნაკლები.')

    def action_check(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids') or []
        moves = self.env['account.move'].browse(active_ids).exists()
        if not moves:
            raise UserError('ინვოისი ვერ მოიძებნა.')
        return moves.check_done_factura_in_period(self.date1, self.date2)
