from odoo import api, models


class NBGCurrencyUpdateJob(models.Model):
    _name = "nbg.currency.update.job"
    _description = "Scheduled job for currency update"

    @api.model
    def update_rates_daily(self):
        self.env['nbg.currency.update'].create({}).update_today_rates()

