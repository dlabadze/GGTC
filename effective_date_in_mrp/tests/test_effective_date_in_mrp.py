from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase


class TestEffectiveDateInMrp(TransactionCase):
    def test_effective_date_context_uses_local_date(self):
        production = self.env["mrp.production"].new(
            {"effective_date_in_mrp": "2026-05-05 20:30:00"}
        )
        production = production.with_context(tz="Asia/Tbilisi")

        context_data = production._get_effective_date_context()

        self.assertEqual(
            fields.Date.to_string(context_data["force_period_date"]),
            "2026-05-06",
        )

    def test_button_mark_done_requires_effective_date(self):
        production = self.env["mrp.production"].new({})
        production.effective_date_in_mrp = False

        with self.assertRaises(UserError):
            production.button_mark_done()

