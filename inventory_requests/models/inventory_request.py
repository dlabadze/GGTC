from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class InventoryRequestStage(models.Model):
    _name = 'inventory.request.stage'
    _description = 'Inventory Request Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    fold = fields.Boolean(string='Folded in Kanban',
                          help="This stage is folded in the kanban view when there are no records in that stage to display.")

    # Color for progress bar
    color = fields.Integer(string='Color Index', default=0)

    # Whether this stage is done
    is_done = fields.Boolean(string='Is Done Stage',
                             help="If checked, requests in this stage are considered as done.")


class InventoryRequestTag(models.Model):
    _name = 'inventory.request.tag'
    _description = 'Inventory Request Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)


class InventoryRequest(models.Model):
    _name = 'inventory.request'
    _description = 'Inventory Request'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # # Computed state field for Studio compatibility
    # state = fields.Char(
    #     string='Status',
    #     compute='_compute_state',
    #     store=False
    # )
    #
    # @api.depends('stage_id')
    # def _compute_state(self):
    #     for record in self:
    #         record.state = record.stage_id.name if record.stage_id else 'draft'

    status_request = fields.Selection([
        ('no', 'არა'),
        ('yes', 'ხელშეკრულება გაფორმებულია')
    ], string='Status', default='no', tracking=True)

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')

    # Dynamic stage instead of static selection
    stage_id = fields.Many2one(
        'inventory.request.stage',
        string='Stage',
        index=True,
        copy=False,
        group_expand='_read_group_stage_ids'  # This ensures empty stages appear
    )

    # Tags field
    tag_ids = fields.Many2many(
        'inventory.request.tag',
        string='Tags'
    )

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user,
                                   required=True)
    department_id = fields.Many2one('hr.department', string='Department', ondelete='set null')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Very High')
    ], string='Priority', default='1')

    description = fields.Text(string='Description')
    line_ids = fields.One2many('inventory.line', 'request_id', string='Inventory Lines')

    # Computed fields
    total_lines = fields.Integer(string='Total Lines', compute='_compute_totals', store=True)

    @api.depends('line_ids')
    def _compute_totals(self):
        for request in self:
            request.total_lines = len(request.line_ids)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        """Always return all active stages, even if they're empty"""
        # Get all active stages
        all_stages = self.env['inventory.request.stage'].search([('active', '=', True)], order='sequence, name')
        return all_stages

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('inventory.request') or 'New'
            # Set default stage if not provided
            if not vals.get('stage_id'):
                default_stage = self.env['inventory.request.stage'].search([('active', '=', True)], limit=1,
                                                                           order='sequence')
                if default_stage:
                    vals['stage_id'] = default_stage.id
        return super().create(vals_list)

    def unlink(self):
        """Update budget lines and purchase plan lines when request is deleted"""
        # Collect all affected budget lines and purchase plan lines from all lines in the requests
        purchase_plan_combinations = set()
        budget_line_combinations = set()

        for request in self:
            for line in request.line_ids:
                if line.x_studio_purchase_plan and line.x_studio_purchase_plan_line:
                    purchase_plan_combinations.add(
                        (line.x_studio_purchase_plan.id, line.x_studio_purchase_plan_line.id))
                if line.budget_analytic and line.budget_analytic_line:
                    budget_line_combinations.add((line.budget_analytic.id, line.budget_analytic_line.id))

        # Delete the request (cascade will delete lines)
        result = super().unlink()

        # Update affected combinations after deletion
        InventoryLine = self.env['inventory.line']
        for purchase_plan_id, purchase_plan_line_id in purchase_plan_combinations:
            InventoryLine._update_purchase_plan_reservation_combined(purchase_plan_id, purchase_plan_line_id)

        for budget_analytic_id, budget_line_id in budget_line_combinations:
            InventoryLine._update_budget_line_reservation_combined(budget_analytic_id, budget_line_id)

        _logger.info(f"Updated {len(purchase_plan_combinations)} purchase plan lines and {len(budget_line_combinations)} budget lines after request deletion")

        return result
    
    







    
