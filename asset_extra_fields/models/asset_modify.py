from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class AssetModify(models.TransientModel):
	_inherit = 'asset.modify'

	def _ae_adjust_amounts_on_move(self, asset, move):
		"""Adjust ONLY amounts on existing lines: asset, accumulated dep, and balance on existing P&L line.
		No new lines, no account changes.
		"""
		try:
			add_original = float(asset.original_value_new or 0.0)
			add_already_dep = float(asset.already_depreciated_amount_import_new or 0.0)
			# Snapshot BEFORE
			before = []
			for l in move.line_ids:
				acc = l.account_id
				before.append({
					'line_id': getattr(l, 'id', None),
					'account_id': acc.id if acc else None,
					'account': (f"{getattr(acc, 'code', '')} {getattr(acc, 'name', '')}".strip() if acc else ''),
					'name': l.name or '',
					'debit': float(l.debit or 0.0),
					'credit': float(l.credit or 0.0),
					'amount_currency': float(getattr(l, 'amount_currency', 0.0) or 0.0),
				})
			_logger.info('[AE] Start asset_id=%s move_id=%s add_original=%.6f add_already_dep=%.6f BEFORE=%s', getattr(asset, 'id', None), getattr(move, 'id', None), add_original, add_already_dep, before)
			if not add_original and not add_already_dep:
				return
			asset_acc_id = asset.account_asset_id.id if asset.account_asset_id else 0
			accum_acc_id = asset.account_depreciation_id.id if asset.account_depreciation_id else 0
			asset_line = None
			accum_line = None
			pl_line = None
			for l in move.line_ids:
				acc_id = l.account_id.id if l.account_id else 0
				if acc_id == asset_acc_id and asset_line is None:
					asset_line = l
				elif acc_id == accum_acc_id and accum_line is None:
					accum_line = l
				elif not pl_line and l.account_id and getattr(l.account_id, 'internal_group', None) in ('income', 'expense'):
					pl_line = l
			# Fallbacks to detect accumulated depreciation line more robustly
			if not accum_line:
				candidates = [
					ln for ln in move.line_ids
					if ln.account_id
					and ln.account_id.id != asset_acc_id
					and getattr(ln.account_id, 'internal_group', None) not in ('income', 'expense')
				]
				# 1) Prefer account_depreciation_id exact match
				accum_line = next((ln for ln in candidates if ln.account_id.id == accum_acc_id), None)
				# 2) If still not found, prefer the largest absolute amount (typical accum dep line)
				if not accum_line and candidates:
					accum_line = max(candidates, key=lambda ln: abs(float(ln.debit or 0.0) - float(ln.credit or 0.0)))
				# 3) If asset line is credit-only (dispose), prefer a candidate with debit > 0
				if not accum_line and candidates and asset_line and asset_line.credit and not asset_line.debit:
					accum_line = next((ln for ln in candidates if (ln.debit or 0.0) > 0.0), None) or candidates[0]
			# Log chosen lines
			try:
				_logger.info('[AE] Lines chosen asset_line=%s accum_line=%s pl_line=%s', getattr(asset_line, 'id', None), getattr(accum_line, 'id', None), getattr(pl_line, 'id', None))
			except Exception:
				pass
			# Prepare batched writes to avoid interim imbalance errors
			updates = []
			if asset_line and add_original:
				new_vals = {}
				if float(asset_line.credit or 0.0) > 0.0:
					new_vals['credit'] = float(asset_line.credit or 0.0) + add_original
				else:
					new_vals['debit'] = float(asset_line.debit or 0.0) + add_original
				updates.append((1, asset_line.id, new_vals))
			if accum_line and add_already_dep:
				# Always increase accumulated depreciation on the DEBIT side during dispose
				new_vals = {'debit': float(accum_line.debit or 0.0) + add_already_dep}
				updates.append((1, accum_line.id, new_vals))
			elif add_already_dep:
				_logger.warning('[AE] Could not locate accumulated depreciation line to add %.6f', add_already_dep)
			# balance totals on existing P&L line
			# Compute delta after applying planned updates (in-memory simulation)
			planned_totals = {
				asset_line.id if asset_line else None: updates[0][2] if updates and updates[0][1] == (asset_line.id if asset_line else -1) else {},
				accum_line.id if accum_line else None: next((u[2] for u in updates if accum_line and u[1] == accum_line.id), {}),
			}
			total_debit = 0.0
			total_credit = 0.0
			for l in move.line_ids:
				vals = planned_totals.get(l.id) or {}
				deb = float(vals.get('debit', l.debit or 0.0))
				cre = float(vals.get('credit', l.credit or 0.0))
				total_debit += deb
				total_credit += cre
			delta = round(total_debit - total_credit, 2)
			if pl_line and delta:
				pl_vals = {}
				if delta > 0:
					pl_vals['credit'] = float(pl_line.credit or 0.0) + abs(delta)
				else:
					pl_vals['debit'] = float(pl_line.debit or 0.0) + abs(delta)
				updates.append((1, pl_line.id, pl_vals))
			# Apply all updates in one batched write to avoid interim balance checks
			if updates:
				_logger.info('[AE] Batched updates: %s', updates)
				move.with_context(check_move_validity=False).write({'line_ids': updates})
			# Snapshot AFTER
			after = []
			for l in move.line_ids:
				acc = l.account_id
				after.append({
					'line_id': getattr(l, 'id', None),
					'account_id': acc.id if acc else None,
					'account': (f"{getattr(acc, 'code', '')} {getattr(acc, 'name', '')}".strip() if acc else ''),
					'name': l.name or '',
					'debit': float(l.debit or 0.0),
					'credit': float(l.credit or 0.0),
					'amount_currency': float(getattr(l, 'amount_currency', 0.0) or 0.0),
				})
			LoggerTotalsDebit = sum((x.debit or 0.0) for x in move.line_ids)
			LoggerTotalsCredit = sum((x.credit or 0.0) for x in move.line_ids)
			_logger.info('[AE] Done move_id=%s AFTER=%s totals debit=%.2f credit=%.2f', getattr(move, 'id', None), after, LoggerTotalsDebit, LoggerTotalsCredit)
		except Exception as e:
			_logger.exception('[AE] Wizard adjust failed: %s', e)

	def sell_dispose(self):
		"""Call super, then adjust amounts on the created move without changing accounts/structure."""
		action = super().sell_dispose()
		res_model = action.get('res_model') if isinstance(action, dict) else None
		res_id = action.get('res_id') if isinstance(action, dict) else None
		if res_model == 'account.move' and res_id:
			move = self.env['account.move'].browse(res_id)
			for wiz in self:
				asset = wiz.asset_id
				if asset and move and move.exists():
					self._ae_adjust_amounts_on_move(asset, move)
		return action


