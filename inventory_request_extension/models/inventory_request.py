import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InventoryRequest(models.Model):
    _inherit = 'inventory.request'

    users_in_lines = fields.Many2many('res.users', string='იუზერები განფასებაში', compute='_compute_users_in_lines', store=True)
    stage_id = fields.Many2one(
        'inventory.request.stage',
        string='Stage',
        index=True,
        copy=False,
        group_expand='_read_group_stage_ids',
        tracking=True,
    )
    is_returned = fields.Boolean(string='დაბრუნებული', default=False)
    september_request_ids = fields.Many2many('september.request', string='September Requests')
    active = fields.Boolean(string='Active', default=True)

    @api.depends('line_ids', 'line_ids.ganawileba_user_id')
    def _compute_users_in_lines(self):
        for request in self:
            if request.line_ids:
                request.users_in_lines = request.line_ids.mapped('ganawileba_user_id')
            else:
                request.users_in_lines = False

    def action_duplicate_checked_lines(self):
        """Duplicate checked lines (is_checked) into the same request."""
        for request in self:
            checked_lines = request.line_ids.filtered(lambda l: l.is_checked)
            if not checked_lines:
                continue
            for line in checked_lines:
                # Use copy_data to safely duplicate values
                values = line.copy_data()[0]
                values['request_id'] = request.id
                # Reset the checkbox on the duplicated line
                values['is_checked'] = False
                # Create duplicated line
                request.env['inventory.line'].create(values)

    def ganawileba_action(self):
        """Open wizard to select user for ganawileba"""
        self.ensure_one()
        return {
            'name': 'Select User for Ganawileba',
            'type': 'ir.actions.act_window',
            'res_model': 'ganawileba.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
            }
        }

    def action_update_from_september(self):
        """
        Update budget_analytic_line on inventory lines from linked September request.
        For each checked inventory.request with september_request_ids, use the first
        september.request to match lines by product_id and set budget_analytic_line
        from sep_line.budget_name_main + budget.analytic "ხარჯები 2026".
        """
        if not self:
            return

        # Search budget.analytic with name="ხარჯები 2026" once
        budget_analytic = self.env['budget.analytic'].search([
            ('name', '=', 'ხარჯები 2026')
        ], limit=1)
        if not budget_analytic:
            _logger.warning("budget.analytic with name 'ხარჯები 2026' not found")
            raise UserError(_("ბიუჯეტი 'ხარჯები 2026' ვერ მოიძებნა"))

        # Determine budget.line field for budget relation
        budget_line_fields = self.env['budget.line']._fields.keys()
        possible_budget_fields = ['budget_analytic_id', 'budget_id', 'analytic_budget_id', 'budget_main_id']
        budget_field_name = next((f for f in possible_budget_fields if f in budget_line_fields), None)

        updated_count = 0
        for request in self:
            if not request.september_request_ids:
                continue

            sep_request = request.september_request_ids

            for inv_line in request.line_ids:
                if not inv_line.product_id:
                    continue

                matching_sep_lines = sep_request.line_ids.filtered(
                    lambda l: l.product_id == inv_line.product_id
                )
                if not matching_sep_lines:
                    continue
                sep_line = matching_sep_lines[:1]
                if not sep_line.budget_name_main:
                    continue

                # Search budget.line by account_id (budget_name_main) + budget_analytic_id
                domain = [
                    ('account_id', '=', sep_line.budget_name_main.id),
                ]
                if budget_field_name:
                    domain.append((budget_field_name, '=', budget_analytic.id))

                budget_line = self.env['budget.line'].search(domain, limit=1)
                if not budget_line and budget_field_name:
                    # Fallback: search without budget constraint
                    budget_line = self.env['budget.line'].search([
                        ('account_id', '=', sep_line.budget_name_main.id),
                    ], limit=1)

                if budget_line:
                    inv_line.with_context(skip_budget_auto_fill=True).write({
                        'budget_analytic_line': budget_line.id,
                        'budget_analytic': budget_analytic.id,
                        'budget_name_main': sep_line.budget_name_main.id,
                    })
                    updated_count += 1

        if updated_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('განახლება'),
                    'message': _('%s ხაზი განახლდა') % updated_count,
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_update_from_september_from_old_request(self):
        """
        Same as action_update_from_september but uses september_request_id (Many2one)
        to find september.line via request.september_request_id.line_ids.
        First action uses september_request_ids (Many2many), this one uses september_request_id.
        """
        if not self:
            return

        budget_analytic = self.env['budget.analytic'].search([
            ('name', '=', 'ხარჯები 2026')
        ], limit=1)
        if not budget_analytic:
            _logger.warning("budget.analytic with name 'ხარჯები 2026' not found")
            raise UserError(_("ბიუჯეტი 'ხარჯები 2026' ვერ მოიძებნა"))

        budget_line_fields = self.env['budget.line']._fields.keys()
        possible_budget_fields = ['budget_analytic_id', 'budget_id', 'analytic_budget_id', 'budget_main_id']
        budget_field_name = next((f for f in possible_budget_fields if f in budget_line_fields), None)

        updated_count = 0
        for request in self:
            if not getattr(request, 'september_request_id', None) or not request.september_request_id:
                continue

            sep_request = request.september_request_id

            for inv_line in request.line_ids:
                if not inv_line.product_id:
                    continue

                matching_sep_lines = sep_request.line_ids.filtered(
                    lambda l: l.product_id == inv_line.product_id
                )
                if not matching_sep_lines:
                    continue
                sep_line = matching_sep_lines[:1]
                if not sep_line.budget_name_main:
                    continue

                domain = [
                    ('account_id', '=', sep_line.budget_name_main.id),
                ]
                if budget_field_name:
                    domain.append((budget_field_name, '=', budget_analytic.id))

                budget_line = self.env['budget.line'].search(domain, limit=1)
                if not budget_line and budget_field_name:
                    budget_line = self.env['budget.line'].search([
                        ('account_id', '=', sep_line.budget_name_main.id),
                    ], limit=1)

                if budget_line:
                    inv_line.with_context(skip_budget_auto_fill=True).write({
                        'budget_analytic_line': budget_line.id,
                        'budget_analytic': budget_analytic.id,
                        'budget_name_main': sep_line.budget_name_main.id,
                    })
                    updated_count += 1

        if updated_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('განახლება'),
                    'message': _('%s ხაზი განახლდა') % updated_count,
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_update_budget_analytic(self):
        if not self:
            return
        budget_analytic = self.env['budget.analytic'].search([
            ('name', '=', 'ხარჯები 2026')
        ], limit=1)
        if not budget_analytic:
            _logger.warning("budget.analytic with name 'ხარჯები 2026' not found")
            raise UserError(_("ბიუჯეტი 'ხარჯები 2026' ვერ მოიძებნა"))
        for rec in self:
            lines = rec.line_ids.filtered(lambda l: l.budget_name_main)
            for line in lines:
                budget_line = self.env['budget.line'].search([
                    ('account_id', '=', line.budget_name_main.id),
                    ('budget_analytic_id', '=', budget_analytic.id)
                ], limit=1)
                if budget_line:
                    budget_line.write({
                        'x_studio_reserved': line.amount
                    })

    def write(self, vals):
        if 'stage_id' in vals:
            new_stage = self.env['inventory.request.stage'].browse(vals['stage_id'])
            
            if new_stage.name == 'ბაზრის კვლევა და განფასება':
                for record in self:
                    # Check if users_in_lines is empty
                    if not record.users_in_lines:
                        # Don't change the stage, keep the old one
                        vals.pop('stage_id')
                        # Show warning message
                        raise UserError('იუზერები განფასებაში ველი უნდა იყოს შევსებული')
        
        return super(InventoryRequest, self).write(vals)