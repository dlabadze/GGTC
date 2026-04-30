import logging

_logger = logging.getLogger(__name__)


def create_missing_budget_line_changes(env):
    """Create budget.line.changes records for all existing expense budget lines that don't have one."""
    lines = env['budget.line'].search([
        ('budget_analytic_id.budget_type', '=', 'expense'),
        ('budget_change_id', '=', False),
    ])
    _logger.info("post_init_hook: found %d expense budget lines without a changes record", len(lines))

    Change = env['budget.line.changes']
    max_id = Change.search([], order='custom_id desc', limit=1).custom_id or 0

    for record in lines:
        max_id += 1
        change = Change.create({
            'custom_id': max_id,
            'budget_line_id': record.id,
        })
        record.write({'budget_change_id': change.id})
        _logger.info("  created changes record id=%s for budget.line id=%s", change.id, record.id)

    _logger.info("post_init_hook: done. created %d changes records", len(lines))
