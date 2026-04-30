from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)
_logger.disabled = True


class AccountAsset(models.Model):
	_inherit = 'account.asset'

	original_value_new = fields.Float(string='Original Value (New)')
	old_depre = fields.Float(string='Old Depreciation')
	already_depreciated_amount_import_new = fields.Float(string='Already Depreciated (Import New)')
	
	# ჯამური ველები (Computed)
	full_depreciated_amount = fields.Monetary(
		string='ჯამური დარიცხული ცვეთა',
		compute='_compute_full_amounts',
		store=True,
		currency_field='currency_id',
		help='ჯამური დარიცხული ცვეთა = იმპორტირებული ცვეთა + Odoo-ში დარიცხული ცვეთა'
	)
	
	full_original_value_new = fields.Monetary(
		string='ჯამური საწყისი ღირებულება',
		compute='_compute_full_amounts',
		store=True,
		currency_field='currency_id',
		help='ჯამური საწყისი ღირებულება = original_value_new + original_value'
	)
	
	@api.depends(
		'already_depreciated_amount_import_new',
		'depreciation_move_ids.state',
		'depreciation_move_ids.asset_depreciated_value',
		'original_value_new',
		'original_value'
	)
	def _compute_full_amounts(self):
		"""
		გამოთვლის ჯამურ ღირებულებებს:
		1. full_depreciated_amount = already_depreciated_amount_import_new + ჯამი(posted depreciation entries)
		2. full_original_value_new = original_value_new + original_value
		"""
		for asset in self:
			# 1. ჯამური დარიცხული ცვეთა
			# იმპორტირებული ცვეთა
			imported_depreciation = asset.already_depreciated_amount_import_new or 0.0
			
			# Odoo-ში დარიცხული ცვეთა (მხოლოდ posted ჩანაწერები)
			posted_depreciation = sum(
				move.asset_depreciated_value
				for move in asset.depreciation_move_ids
				if move.state == 'posted'
			)
			
			asset.full_depreciated_amount = imported_depreciation + posted_depreciation
			
			# 2. ჯამური საწყისი ღირებულება
			asset.full_original_value_new = (asset.original_value_new or 0.0) + (asset.original_value or 0.0)

	def _adjust_sell_dispose_move_lines(self, move_lines):
		try:
			self.ensure_one()
			if not move_lines:
				return move_lines
			_logger.info('[AE] (_adjust) asset_id=%s incoming lines=%s', self.id, move_lines)
			add_original = float(self.original_value_new or 0.0)
			add_already_dep = float(self.already_depreciated_amount_import_new or 0.0)
			if not add_original and not add_already_dep:
				_logger.info('[AE] (_adjust) no extras for asset_id=%s → passthrough', self.id)
				return move_lines
			# Create a shallow copy to avoid mutating caller's list unexpectedly
			new_lines = [dict(l) for l in move_lines]
			asset_acc_id = getattr(self, 'account_asset_id', False).id if getattr(self, 'account_asset_id', False) else 0
			accum_acc_id = getattr(self, 'account_depreciation_id', False).id if getattr(self, 'account_depreciation_id', False) else 0
			asset_line = None
			accum_line = None
			pl_line = None
			for vals in new_lines:
				acc_id = vals.get('account_id')
				if acc_id == asset_acc_id and asset_line is None:
					asset_line = vals
				elif acc_id == accum_acc_id and accum_line is None:
					accum_line = vals
				else:
					pl_line = pl_line or vals
			# Adjust asset line by add_original (credit on dispose; if debit present, increase debit instead)
			if asset_line and add_original:
				if float(asset_line.get('credit') or 0.0) > 0.0:
					asset_line['credit'] = float(asset_line['credit']) + add_original
				else:
					asset_line['debit'] = float(asset_line.get('debit') or 0.0) + add_original
			# Adjust accumulated depreciation line by add_already_dep (usually debit on dispose)
			if accum_line and add_already_dep:
				if float(accum_line.get('debit') or 0.0) > 0.0:
					accum_line['debit'] = float(accum_line['debit']) + add_already_dep
				else:
					accum_line['credit'] = float(accum_line.get('credit') or 0.0) + add_already_dep
			# Recompute totals and set P&L line to balance exactly, without creating new lines
			total_debit = sum(float(v.get('debit') or 0.0) for v in new_lines)
			total_credit = sum(float(v.get('credit') or 0.0) for v in new_lines)
			delta = round(total_debit - total_credit, 2)
			if delta and pl_line:
				# If delta > 0, need more credit; else need more debit
				if delta > 0:
					pl_line['credit'] = float(pl_line.get('credit') or 0.0) + abs(delta)
				else:
					pl_line['debit'] = float(pl_line.get('debit') or 0.0) + abs(delta)
				# Recompute after fix (diagnostic log)
				final_debit = sum(float(v.get('debit') or 0.0) for v in new_lines)
				final_credit = sum(float(v.get('credit') or 0.0) for v in new_lines)
				_logger.info('[AE] (_adjust) balanced via P&L line; final debit=%.2f credit=%.2f', final_debit, final_credit)
			else:
				_logger.info('[AE] (_adjust) no P&L line found or already balanced; delta=%.2f', delta)
			_logger.info('[AE] (_adjust) asset_id=%s adjusted lines=%s', self.id, new_lines)
			return new_lines
		except Exception as e:
			_logger.exception('[AE] (_adjust) failed: %s', e)
			return move_lines

	# Odoo 18 method names may differ; try to hook common ones defensively.
	def _get_disposal_move_lines(self, **kwargs):
		try:
			_logger.info('[AE] _get_disposal_move_lines called asset_id=%s kwargs=%s', self.id, kwargs)
			lines = super()._get_disposal_move_lines(**kwargs) if hasattr(super(), '_get_disposal_move_lines') else None
			if lines is not None:
				adj = self._adjust_sell_dispose_move_lines(lines)
				_logger.info('[AE] _get_disposal_move_lines result len=%s', len(adj) if adj else 0)
				return adj
			return lines
		except Exception as e:
			_logger.exception('[AE] _get_disposal_move_lines failed: %s', e)
			return super()._get_disposal_move_lines(**kwargs) if hasattr(super(), '_get_disposal_move_lines') else None

	def _get_sell_move_lines(self, **kwargs):
		try:
			_logger.info('[AE] _get_sell_move_lines called asset_id=%s kwargs=%s', self.id, kwargs)
			lines = super()._get_sell_move_lines(**kwargs) if hasattr(super(), '_get_sell_move_lines') else None
			if lines is not None:
				adj = self._adjust_sell_dispose_move_lines(lines)
				_logger.info('[AE] _get_sell_move_lines result len=%s', len(adj) if adj else 0)
				return adj
			return lines
		except Exception as e:
			_logger.exception('[AE] _get_sell_move_lines failed: %s', e)
			return super()._get_sell_move_lines(**kwargs) if hasattr(super(), '_get_sell_move_lines') else None


