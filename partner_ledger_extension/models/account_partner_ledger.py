from odoo import models
from odoo.tools import SQL


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"

    def _get_additional_column_aml_values(self):
        """Add move comment (account.move.comment) and a NULL placeholder for
        partner_vat so the base handler finds both in the SQL result. Comment
        is visible on each move line when the partner row is expanded."""
        return SQL("account_move.comment AS move_comment, NULL AS partner_vat,")

    def _get_report_line_partners(self, options, partner, partner_values, level_shift=0):
        """Show the partner VAT in the Partner VAT column on grouped partner
        header lines only. Move lines show an empty cell automatically."""
        line = super()._get_report_line_partners(
            options, partner, partner_values, level_shift=level_shift
        )

        if partner and line.get("columns"):
            vat = partner.vat or ""
            for idx, col in enumerate(options["columns"]):
                if col["expression_label"] == "partner_vat" and idx < len(line["columns"]):
                    line["columns"][idx] = {"name": vat, "no_format": vat}
                    break

        return line
