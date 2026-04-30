# -*- coding: utf-8 -*-

from odoo import _, models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _dv_fix_valuation_to_standard_price(self):
        """
        Adjust (in-place) stock valuation and related accounting entries so that valuation equals
        product Standard Price × quantity.

        This method edits the existing valuation-linked journal entries by:
        - moving them to draft
        - updating the valuation-linked lines (debit/credit) while keeping balance = 0
        - re-posting the move

        Notes:
        - Only applies to real-time valuation products.
        - Requires that related journal entries can be reset to draft (no lock dates / restrictions).
        """
        AccountMove = self.env["account.move"].sudo()
        AccountMoveLine = self.env["account.move.line"].sudo()

        for move in self:
            move = move.with_company(move.company_id)
            if not move.product_id.is_storable:
                continue
            if move.product_id.valuation != "real_time":
                continue

            # -----------------------------------------------------------------
            # 1) Ensure SVL exists and fix SVL values first (even if no JE exists).
            # -----------------------------------------------------------------
            if not move.stock_valuation_layer_ids and (move._is_out() or move.scrapped):
                move._create_out_svl()

            svls_all = move.stock_valuation_layer_ids.sudo()
            for svl in svls_all:
                desired_value = move.product_id.standard_price * svl.quantity
                if not svl.currency_id.is_zero(desired_value - svl.value):
                    svl.write({"value": desired_value})

            # -----------------------------------------------------------------
            # 2) If there was no JE because valuation was 0 at the time, generate it now
            #    using the standard stock_account mechanism.
            # -----------------------------------------------------------------
            svls_missing_je = svls_all.filtered(lambda l: not l.account_move_id and not l.currency_id.is_zero(l.value))
            if svls_missing_je:
                svls_missing_je._validate_accounting_entries()
                svls_missing_je._validate_analytic_accounting_entries()

            # Stock valuation journal entries are linked to the move through account.move.stock_move_id.
            account_moves = (move.account_move_ids | svls_all.mapped("account_move_id")).sudo().exists()
            for account_move in account_moves:
                if not account_move:
                    continue

                company_currency = account_move.company_id.currency_id

                # Reset to draft to allow editing.
                if account_move.state == "posted":
                    (account_move.line_ids.filtered("reconciled")).remove_move_reconcile()
                    account_move.button_draft()

                # Get SVLs linked to this journal entry (usually 1 per move, but keep it generic).
                svls = svls_all.filtered(lambda l: l.account_move_id.id == account_move.id)
                if not svls:
                    continue

                # Update AMLs (in-place) by account ids, like Odoo tests do.
                _journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
                valuation_lines = account_move.line_ids.filtered(lambda l: l.account_id.id == acc_valuation)
                counterpart_lines = account_move.line_ids.filtered(lambda l: l.account_id.id in (acc_src, acc_dest) and l.account_id.id != acc_valuation)

                valuation_line = valuation_lines[:1]
                counterpart_line = counterpart_lines[:1]
                if not valuation_line or not counterpart_line:
                    # Fallback: take one non-display line with nonzero balance besides valuation.
                    valuation_line = valuation_line or account_move.line_ids.filtered(lambda l: l.account_id.id == acc_valuation)[:1]
                    counterpart_line = counterpart_line or (account_move.line_ids.filtered(lambda l: not l.display_type and l.account_id.id != acc_valuation and not company_currency.is_zero(l.balance))[:1])
                if not valuation_line or not counterpart_line:
                    continue

                new_total = company_currency.round(sum(svls.mapped("value")))

                ctx = dict(self.env.context, check_move_validity=False, skip_account_move_synchronization=True)
                AccountMoveLine.with_context(ctx).browse(valuation_line.id).write({
                    "balance": new_total,
                    "amount_currency": new_total if (not valuation_line.currency_id or valuation_line.currency_id == company_currency) else valuation_line.amount_currency,
                })
                AccountMoveLine.with_context(ctx).browse(counterpart_line.id).write({
                    "balance": -new_total,
                    "amount_currency": -new_total if (not counterpart_line.currency_id or counterpart_line.currency_id == company_currency) else counterpart_line.amount_currency,
                })

                # Re-post.
                if account_move.state == "draft":
                    AccountMove.browse(account_move.id)._post()

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        moves = (self | res).exists()
        moves_to_fix = moves.filtered(
            lambda m: m.state == "done"
            and (
                (
                    m.scrapped
                    and m.scrap_id
                    and m.scrap_id.dv_fix_valuation_to_standard_price
                )
                or (
                    m.picking_id
                    and (
                        m.picking_id.picking_type_code == "outgoing"
                        or m.picking_id.location_dest_id.scrap_location
                    )
                    and m.picking_id.dv_fix_valuation_to_standard_price
                )
            )
        )
        if moves_to_fix:
            moves_to_fix._dv_fix_valuation_to_standard_price()
        return res

