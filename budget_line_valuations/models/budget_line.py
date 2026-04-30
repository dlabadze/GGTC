from odoo import api, fields, models


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    valuation_product_filter_id = fields.Many2one(
        'product.product',
        string='პროდუქტით ძებნა',
    )
    valuation_date_start = fields.Date(string='Start Date')
    valuation_date_end = fields.Date(string='End Date')
    payment_product_filter_id = fields.Many2one(
        'product.product',
        string='პროდუქტით ძებნა',
    )
    payment_date_start = fields.Date(string='Start Date')
    payment_date_end = fields.Date(string='End Date')
    valuations_ids = fields.Many2many(
        'stock.valuation.layer',
        compute='_compute_valuations_ids',
        string='Valuations',
        store=False,
    )
    payment_move_line_ids = fields.Many2many(
        'account.move.line',
        compute='_compute_payment_move_line_ids',
        string='Payments',
        store=False,
    )
    bill_ids = fields.Many2many(
        'account.move.line',
        compute='_compute_bill_ids',
        string='Bills',
        store=False,
    )
    muxli_move_ids = fields.Many2many(
        'account.move',
        compute='_compute_muxli_move_ids',
        string='Journal Entries',
        store=False,
    )

    @staticmethod
    def _extract_distribution_account_ids(analytic_distribution):
        account_ids = set()
        if not isinstance(analytic_distribution, dict):
            return account_ids

        for key in analytic_distribution.keys():
            key_parts = str(key).split(',')
            for key_part in key_parts:
                key_part = key_part.strip()
                if key_part.isdigit():
                    account_ids.add(int(key_part))
        return account_ids

    @api.depends('valuation_product_filter_id', 'valuation_date_start', 'valuation_date_end')
    def _compute_valuations_ids(self):
        for record in self:
            inv_lines = self.env['inventory.line'].search([
                ('budget_analytic_line', '=', record.id)
            ])
            if not inv_lines:
                record.valuations_ids = False
                continue

            all_move_ids = set()
            for inv_line in inv_lines:
                req_name = inv_line.request_id.name
                product = inv_line.product_id
                if not req_name or not product:
                    continue
                moves = self.env['stock.move'].search([
                    ('origin', '=', req_name),
                    ('product_id', '=', product.id),
                    ('picking_id.state', '=', 'done'),
                    ('picking_id.location_dest_id', '=', 16),
                ])
                all_move_ids.update(moves.ids)

            if not all_move_ids:
                record.valuations_ids = False
                continue

            valuations = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', list(all_move_ids))
            ])
            if record.valuation_product_filter_id:
                valuations = valuations.filtered(
                    lambda valuation: valuation.product_id.id == record.valuation_product_filter_id.id
                )
            if record.valuation_date_start:
                valuations = valuations.filtered(
                    lambda valuation: valuation.create_date and valuation.create_date.date() >= record.valuation_date_start
                )
            if record.valuation_date_end:
                valuations = valuations.filtered(
                    lambda valuation: valuation.create_date and valuation.create_date.date() <= record.valuation_date_end
                )
            record.valuations_ids = valuations if valuations else False

    @api.depends('account_id', 'payment_product_filter_id', 'payment_date_start', 'payment_date_end')
    def _compute_payment_move_line_ids(self):
        empty_lines = self.env['account.move.line']
        records_with_account = self.filtered('account_id')
        account_ids = set(records_with_account.mapped('account_id').ids)

        distribution_map = {account_id: empty_lines for account_id in account_ids}
        if account_ids:
            product_filter_ids = set(records_with_account.mapped('payment_product_filter_id').ids)
            for product_id in product_filter_ids | {False}:
                candidate_domain = [
                    ('analytic_distribution', '!=', False),
                    ('move_id.state', '=', 'posted'),
                ]
                if product_id:
                    candidate_domain.append(('product_id', '=', product_id))

                candidate_lines = self.env['account.move.line'].search(candidate_domain)
                for line in candidate_lines:
                    analytic_account_ids = self._extract_distribution_account_ids(line.analytic_distribution)
                    for analytic_account_id in analytic_account_ids:
                        if analytic_account_id not in distribution_map:
                            continue
                        distribution_map[analytic_account_id] |= line

        for record in self:
            if not record.account_id:
                record.payment_move_line_ids = False
                continue
            move_lines = distribution_map.get(record.account_id.id, empty_lines)
            if record.payment_product_filter_id:
                move_lines = move_lines.filtered(
                    lambda line: line.product_id.id == record.payment_product_filter_id.id
                )
            if record.payment_date_start:
                move_lines = move_lines.filtered(
                    lambda line: line.date and line.date >= record.payment_date_start
                )
            if record.payment_date_end:
                move_lines = move_lines.filtered(
                    lambda line: line.date and line.date <= record.payment_date_end
                )
            record.payment_move_line_ids = move_lines

    @api.depends(
        'requisition_line_ids',
        'requisition_line_ids.product_id',
        'requisition_line_ids.budget_line_id',
    )
    def _compute_bill_ids(self):
        empty_lines = self.env['account.move.line']
        records_with_requisition_lines = self.filtered('requisition_line_ids')
        lines_by_budget_line = {record.id: empty_lines for record in records_with_requisition_lines}

        if records_with_requisition_lines:
            candidate_lines = self.env['account.move.line'].search([
                ('move_id.move_type', 'in', ('in_invoice', 'in_refund')),
                ('move_id.state', '=', 'posted'),
                # ('move_id.name', '=ilike', 'BILL%'),
                ('product_id', '!=', False),
                ('product_id.type', '=', 'service'),
                ('purchase_line_id', '!=', False),
            ])

            for line in candidate_lines:
                requisition = line.purchase_line_id.order_id.requisition_id
                if not requisition:
                    continue

                matching_requisition_lines = requisition.line_ids.filtered(
                    lambda requisition_line: requisition_line.product_id.id == line.product_id.id
                    and requisition_line.budget_line_id.id in lines_by_budget_line
                )
                for requisition_line in matching_requisition_lines:
                    lines_by_budget_line[requisition_line.budget_line_id.id] |= line

        for record in self:
            record.bill_ids = lines_by_budget_line.get(record.id, empty_lines)

    @api.depends('account_id', 'account_id.display_name')
    def _compute_muxli_move_ids(self):
        empty_moves = self.env['account.move']
        account_display_names = {name for name in self.mapped('account_id.display_name') if name}
        moves_by_account_display_name = {name: empty_moves for name in account_display_names}

        if account_display_names:
            matching_moves = self.env['account.move'].search([
                ('x_studio_muxli_hr', 'in', list(account_display_names)),
                ('state', '=', 'posted'),
            ])
            for move in matching_moves:
                if move.x_studio_muxli_hr in moves_by_account_display_name:
                    moves_by_account_display_name[move.x_studio_muxli_hr] |= move

        for record in self:
            account_display_name = record.account_id.display_name if record.account_id else False
            record.muxli_move_ids = moves_by_account_display_name.get(account_display_name, empty_moves)

    def action_view_valuations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Valuations',
            'res_model': 'stock.valuation.layer',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.valuations_ids.ids)],
            'target': 'current',
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.payment_move_line_ids.ids)],
            'target': 'current',
        }

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.bill_ids.ids)],
            'target': 'current',
        }

    def action_view_muxli_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.muxli_move_ids.ids)],
            'target': 'current',
        }
