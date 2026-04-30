from odoo import models, fields, api


class SeptemberRequestStage(models.Model):
    _name = 'september.request.stage'
    _description = 'September Request Stage'
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


class SeptemberRequestTag(models.Model):
    _name = 'september.request.tag'
    _description = 'September Request Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=0)
    active = fields.Boolean(string='Active', default=True)


class SeptemberRequest(models.Model):
    _name = 'september.request'
    _description = 'September Request'
    _order = 'create_date desc'

    # Computed state field for Studio compatibility
    state = fields.Char(
        string='Status',
        compute='_compute_state',
        store=False
    )

    @api.depends('stage_id')
    def _compute_state(self):
        for record in self:
            record.state = record.stage_id.name if record.stage_id else 'draft'

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')

    # Dynamic stage instead of static selection
    stage_id = fields.Many2one(
        'september.request.stage',
        string='Stage',
        index=True,
        copy=False,
        group_expand='_read_group_stage_ids'  # This ensures empty stages appear
    )

    # Tags field
    tag_ids = fields.Many2many(
        'september.request.tag',
        string='Tags'
    )

    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user,
                                   required=True)
    department_id = fields.Many2one('hr.department', string='Department')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Very High')
    ], string='Priority', default='1')

    description = fields.Text(string='Description')
    line_ids = fields.One2many('september.line', 'request_id', string='September Lines')

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
        all_stages = self.env['september.request.stage'].search([('active', '=', True)], order='sequence, name')
        return all_stages

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('september.request') or 'New'
            # Set default stage if not provided
            if not vals.get('stage_id'):
                default_stage = self.env['september.request.stage'].search([('active', '=', True)], limit=1,
                                                                           order='sequence')
                if default_stage:
                    vals['stage_id'] = default_stage.id
        return super().create(vals_list)