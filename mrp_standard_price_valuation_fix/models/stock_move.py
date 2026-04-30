# -*- coding: utf-8 -*-

import logging

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    def _dv_fix_valuation_to_standard_price(self):
        """
        Adjust (in-place) stock valuation and related accounting entries.

        - **Raw / byproduct (consumption)**: total value = Standard Price × quantity (move UoM).
        - **Main finished product** (MO output = product to manufacture): total value = sum of raw
          material SVL values on this MO, negated (e.g. raw -30 + -20 => finished +50), so it matches
          component cost after those lines are fixed first.

        Only runs for stock moves tied to manufacturing. Other moves are ignored.

        Notes:
        - Only applies to real-time valuation products.
        - Requires that related journal entries can be reset to draft (no lock dates / restrictions).
        """
        AccountMove = self.env["account.move"].sudo()
        AccountMoveLine = self.env["account.move.line"].sudo()

        # Process raw/component lines before the main finished move so SVL sums are up to date.
        ordered = self.sorted(
            key=lambda m: bool(
                m.production_id
                and m._is_in()
                and m.product_id == m.production_id.product_id
            )
        )

        for move in ordered:
            move = move.with_company(move.company_id)
            if not (move.production_id or move.raw_material_production_id):
                _logger.info(
                    "dv_mrp_fix_skip_not_manufacturing move_id=%s",
                    move.id,
                )
                continue
            _logger.info(
                "dv_mrp_fix_start move_id=%s product=%s valuation=%s std_price=%s picking=%s "
                "production_id=%s raw_mo_id=%s is_out=%s is_in=%s scrapped=%s",
                move.id,
                move.product_id.display_name,
                move.product_id.valuation,
                move.product_id.standard_price,
                move.picking_id.name if move.picking_id else None,
                move.production_id.id if move.production_id else None,
                move.raw_material_production_id.id if move.raw_material_production_id else None,
                move._is_out(),
                move._is_in(),
                move.scrapped,
            )
            if move.product_id.valuation != "real_time":
                _logger.warning(
                    "dv_mrp_fix_skip_not_real_time move_id=%s product=%s valuation=%s",
                    move.id,
                    move.product_id.display_name,
                    move.product_id.valuation,
                )
                continue

            if not move.stock_valuation_layer_ids:
                if move._is_out() or move.scrapped:
                    _logger.info("dv_mrp_fix_create_out_svl move_id=%s", move.id)
                    move._create_out_svl()
                elif move._is_in():
                    _logger.info("dv_mrp_fix_create_in_svl move_id=%s", move.id)
                    move._create_in_svl()
                else:
                    _logger.warning(
                        "dv_mrp_fix_no_svl_neither_in_out move_id=%s is_out=%s is_in=%s scrapped=%s",
                        move.id,
                        move._is_out(),
                        move._is_in(),
                        move.scrapped,
                    )

            svls_all = move.stock_valuation_layer_ids.sudo()
            product = move.product_id
            std = product.standard_price
            company_currency = move.company_id.currency_id
            # Use move quantity in product UoM — SVL quantity can differ (UoM drift, lots), which
            # made std_price * svl.quantity wrong (e.g. 60 * 5/6 = 50 while move qty is 1).
            qty_done = move.product_uom._compute_quantity(
                move.quantity,
                product.uom_id,
                rounding_method="HALF-UP",
            )
            total_svl_qty = sum(svls_all.mapped("quantity"))
            is_main_finished = (
                move.production_id
                and move._is_in()
                and move.product_id == move.production_id.product_id
            )

            if float_is_zero(qty_done, precision_rounding=product.uom_id.rounding):
                _logger.warning(
                    "dv_mrp_fix_zero_qty_done move_id=%s quantity=%s qty_done=%s",
                    move.id,
                    move.quantity,
                    qty_done,
                )
            elif not float_is_zero(total_svl_qty, precision_rounding=product.uom_id.rounding):
                if is_main_finished:
                    mo = move.production_id
                    raw_moves = mo.move_raw_ids.filtered(
                        lambda m: m.state == "done" and not m.scrapped
                    )
                    raw_svls = raw_moves.mapped("stock_valuation_layer_ids").sudo()
                    if raw_svls:
                        raw_sum = sum(raw_svls.mapped("value"))
                        target_core = company_currency.round(-raw_sum)
                        if total_svl_qty < 0:
                            target_total = -abs(target_core)
                        else:
                            target_total = target_core
                        _logger.info(
                            "dv_mrp_fix_finished_from_raw move_id=%s mo=%s raw_sum=%s target_total=%s",
                            move.id,
                            mo.name,
                            raw_sum,
                            target_total,
                        )
                    else:
                        target_abs = company_currency.round(abs(std * qty_done))
                        if total_svl_qty < 0:
                            target_total = -target_abs
                        else:
                            target_total = target_abs
                        _logger.info(
                            "dv_mrp_fix_finished_no_raw_svl_fallback_std move_id=%s target_total=%s",
                            move.id,
                            target_total,
                        )
                else:
                    target_abs = company_currency.round(abs(std * qty_done))
                    if total_svl_qty < 0:
                        target_total = -target_abs
                    else:
                        target_total = target_abs
                for svl in svls_all:
                    desired_value = company_currency.round(
                        target_total * (svl.quantity / total_svl_qty)
                    )
                    if not svl.currency_id.is_zero(desired_value - svl.value):
                        svl.write({"value": desired_value})
                _logger.info(
                    "dv_mrp_fix_svl_values move_id=%s qty_done=%s total_svl_qty=%s target_total=%s",
                    move.id,
                    qty_done,
                    total_svl_qty,
                    target_total,
                )

            svls_missing_je = svls_all.filtered(
                lambda l: not l.account_move_id and not l.currency_id.is_zero(l.value)
            )
            svls_missing_je_ids = set(svls_missing_je.ids)
            created_account_move_dates = {}
            if svls_missing_je:
                _logger.info(
                    "dv_mrp_fix_validate_missing_je move_id=%s svl_ids=%s",
                    move.id,
                    svls_missing_je.ids,
                )
                for date, svls_group in svls_missing_je.grouped(
                    lambda l: (
                        fields.Datetime.context_timestamp(l, l.create_date).date()
                        if l.create_date
                        else fields.Date.context_today(l)
                    )
                ).items():
                    svls_group.with_context(force_period_date=date)._validate_accounting_entries()
                    svls_group._validate_analytic_accounting_entries()
                    created_moves = svls_group.mapped("account_move_id").sudo().exists()
                    for am in created_moves:
                        created_account_move_dates[am.id] = date

            account_moves = (move.account_move_ids | svls_all.mapped("account_move_id")).sudo().exists()
            if not account_moves:
                _logger.warning(
                    "dv_mrp_fix_no_account_moves move_id=%s svl_ids=%s svl_values=%s",
                    move.id,
                    svls_all.ids,
                    svls_all.mapped("value"),
                )
            for account_move in account_moves:
                if not account_move:
                    continue

                company_currency = account_move.company_id.currency_id

                if account_move.state == "posted":
                    (account_move.line_ids.filtered("reconciled")).remove_move_reconcile()
                    account_move.button_draft()

                svls = svls_all.filtered(lambda l: l.account_move_id.id == account_move.id)
                if not svls:
                    _logger.info(
                        "dv_mrp_fix_am_no_matching_svl move_id=%s account_move_id=%s",
                        move.id,
                        account_move.id,
                    )
                    continue

                _journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
                accounts_data = move.product_id.product_tmpl_id.get_product_accounts()
                prod_acc = accounts_data.get("production")
                counterpart_account_ids = {acc_src, acc_dest}
                if prod_acc:
                    counterpart_account_ids.add(prod_acc.id)
                valuation_lines = account_move.line_ids.filtered(lambda l: l.account_id.id == acc_valuation)
                counterpart_lines = account_move.line_ids.filtered(
                    lambda l: l.account_id.id in counterpart_account_ids and l.account_id.id != acc_valuation
                )

                valuation_line = valuation_lines[:1]
                counterpart_line = counterpart_lines[:1]
                if not valuation_line or not counterpart_line:
                    valuation_line = valuation_line or account_move.line_ids.filtered(
                        lambda l: l.account_id.id == acc_valuation
                    )[:1]
                    counterpart_line = counterpart_line or (
                        account_move.line_ids.filtered(
                            lambda l: not l.display_type
                            and l.account_id.id != acc_valuation
                            and not company_currency.is_zero(l.balance)
                        )[:1]
                    )
                if not valuation_line or not counterpart_line:
                    _logger.warning(
                        "dv_mrp_fix_no_valuation_aml move_id=%s account_move_id=%s acc_valuation=%s "
                        "acc_src=%s acc_dest=%s aml_accounts=%s",
                        move.id,
                        account_move.id,
                        acc_valuation,
                        acc_src,
                        acc_dest,
                        account_move.line_ids.mapped("account_id").ids,
                    )
                    continue

                new_total = company_currency.round(sum(svls.mapped("value")))
                _logger.info(
                    "dv_mrp_fix_aml_update move_id=%s account_move_id=%s new_total=%s svl_ids=%s",
                    move.id,
                    account_move.id,
                    new_total,
                    svls.ids,
                )

                ctx = dict(self.env.context, check_move_validity=False, skip_account_move_synchronization=True)
                AccountMoveLine.with_context(ctx).browse(valuation_line.id).write({
                    "balance": new_total,
                    "amount_currency": new_total
                    if (not valuation_line.currency_id or valuation_line.currency_id == company_currency)
                    else valuation_line.amount_currency,
                })
                AccountMoveLine.with_context(ctx).browse(counterpart_line.id).write({
                    "balance": -new_total,
                    "amount_currency": -new_total
                    if (not counterpart_line.currency_id or counterpart_line.currency_id == company_currency)
                    else counterpart_line.amount_currency,
                })

                if account_move.state == "draft":
                    is_missing_je_move = (
                        svls_missing_je_ids
                        and any(svl.id in svls_missing_je_ids for svl in account_move.stock_valuation_layer_ids)
                    )
                    target_date = False
                    if is_missing_je_move and created_account_move_dates.get(account_move.id):
                        target_date = created_account_move_dates[account_move.id]
                    elif svls:
                        svl_with_date = svls.filtered(lambda l: l.create_date)[:1]
                        if svl_with_date:
                            target_date = fields.Datetime.context_timestamp(
                                svl_with_date, svl_with_date.create_date
                            ).date()

                    if target_date:
                        account_move.with_context(
                            check_move_validity=False,
                            skip_account_move_synchronization=True,
                        ).write({"date": target_date})
                    try:
                        AccountMove.browse(account_move.id)._post()
                    except ValidationError:
                        if (
                            account_move.name
                            and account_move.name != "/"
                            and not account_move._sequence_matches_date()
                        ):
                            write_vals = {"name": "/"}
                            if target_date:
                                write_vals["date"] = target_date
                            account_move.with_context(
                                check_move_validity=False,
                                skip_account_move_synchronization=True,
                            ).write(write_vals)
                            AccountMove.browse(account_move.id)._post()
                        else:
                            raise
