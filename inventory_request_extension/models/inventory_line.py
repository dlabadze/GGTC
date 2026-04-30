from odoo import models, fields, api
import logging
from collections import defaultdict
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class InventoryLine(models.Model):
    _inherit = 'inventory.line'

    is_checked = fields.Boolean(string='Checked', default=False)
    
    # Field to mark if line exceeds budget limit (for styling)
    exceeds_budget = fields.Boolean(
        string='Exceeds Budget',
        compute='_compute_exceeds_budget',
        store=False,
        help='True if total quantity for this product exceeds budgeting.line quantity'
    )
    is_ganawileba = fields.Boolean(string='განფასება', default=False)
    ganawileba_user_id = fields.Many2one('res.users', string='განფასება')
    x_studio_warehouse = fields.Many2one(
        'stock.location',
        string='გასაცემი საწყობი',
        domain=[('x_studio_request_location', '=', True)]
    )
    active = fields.Boolean(string='Active', default=True)

    def action_ganfaseba(self):
        return {
            'name': 'Select User for Ganfaseba',
            'type': 'ir.actions.act_window',
            'res_model': 'ganfaseba.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_line_ids': self.ids,
            }
        }
    
    def action_dadastureba(self):
        self = self.sudo()
        if not self:
            raise UserError('არასწორი მონაცემები')
        stage = self.env['inventory.request.stage'].search([('name', '=', 'ფინანსური სამმართველო')], limit=1)
        if not stage:
            return
        # Group selected lines by request_id; only update requests where ALL chosen lines have unit_price > 0
        by_request = defaultdict(lambda: self.env['inventory.line'])
        for line in self:
            by_request[line.request_id] |= line
        for request, lines in by_request.items():
            if all(l.unit_price > 0 for l in lines):
                request.stage_id = stage
            else:
                req_info = request.x_studio_request_number or request.name or f'ID {request.id}'
                raise UserError('%s: ერთეულის ფასი უნდა იყოს 0-ზე მეტი' % req_info)

    def _compute_exceeds_budget(self):
        """Compute if line exceeds budget limit based on budgeting.line"""
        for line in self:
            line.exceeds_budget = False
            if not line.request_id or not line.product_id:
                continue
            
            # Check if request has x_studio_selection_field_6ca_1j76p9boc == 'მარაგები'
            request = line.request_id
            if not hasattr(request, 'x_studio_selection_field_6ca_1j76p9boc'):
                continue
            
            if request.x_studio_selection_field_6ca_1j76p9boc != 'მარაგები':
                continue
            
            # Get budget quantity based on dep_code from inventory.request
            # dep_code is from inventory.request, not budgeting.line
            dep_code = False
            if hasattr(request, 'dep_code'):
                dep_code = request.dep_code
            
            # Get the year from line's create_date
            line_year = line.create_date.year if line.create_date else fields.Datetime.now().year
            year_start = fields.Datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).replace(year=line_year)
            year_end = fields.Datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).replace(year=line_year + 1)
            
            # Search for budgeting.line with same product_id and product_id.categ_id
            # Filter by request_id.request_date.year equal to inventory_line create_date.year
            budgeting_lines = self.env['budgeting.line'].search([
                ('x_studio_related_field_441_1j1fsaqsg', '=', line.product_id.categ_id.id),
                ('request_id.request_date', '>=', year_start.date()),
                ('request_id.request_date', '<', year_end.date())
            ])
            
            # Get all inventory.request lines with same product_id, categ_id, and dep_code where x_studio_selection_field_6ca_1j76p9boc == 'მარაგები'
            # Filter by create_date.year matching line's create_date.year
            domain = [
                # ('product_id', '=', line.product_id.id),
                ('product_id.categ_id', '=', line.product_id.categ_id.id),
                ('request_id.x_studio_selection_field_6ca_1j76p9boc', '=', 'მარაგები'),
                ('request_id.september_request_ids', '=', False),
                ('create_date', '>=', year_start),
                ('create_date', '<', year_end)
            ]
            # Add dep_code to domain if it exists
            if dep_code:
                domain.append(('request_id.dep_code', '=', dep_code))
            else:
                domain.append(('request_id.dep_code', '=', False))
            
            all_matching_lines = self.env['inventory.line'].search(domain)
            
            # If no budgeting_lines found, mark all matching lines as red
            if not budgeting_lines:
                # Mark all matching lines as red - since this is a compute method,
                # we mark the current line if it's in the matching group
                # All lines will be computed eventually and marked red
                if all_matching_lines and line.id in all_matching_lines.ids:
                    line.exceeds_budget = True
                continue
            
            budget_quantity = 0.0
            # Sum x_studio_float_field_4nk_1j1fvng8q from all budgeting lines
            sul_sawyobi = 0.0
            quantity = 0.0
            for budget_line in budgeting_lines:
                field_name = None
                if dep_code == "ცფ":
                    field_name = 'x_studio_float_field_607_1j3r255vi'
                elif dep_code == "ცფს":
                    field_name = 'x_studio_float_field_971_1j3r2i8ah'
                elif dep_code == "კს":
                    field_name = 'x_studio_float_field_3bu_1j3r2insu'
                elif dep_code == "ჩფ":
                    field_name = 'x_studio_float_field_7rg_1j3r2j0fc'
                elif dep_code == "ყუ":
                    field_name = 'x_studio_float_field_1p5_1j3r2j88f'
                elif dep_code == "დფ":
                    field_name = 'x_studio_float_field_349_1j3r2jgm8'
                elif dep_code == "ოდო":
                    field_name = 'x_studio_float_field_366_1j3r2jrui'
                elif dep_code == "მეტ":
                    field_name = 'x_studio_float_field_9r_1j3r2kjpn'
                
                if field_name and hasattr(budget_line, field_name):
                    budget_quantity += getattr(budget_line, field_name) or 0.0
                else:
                    budget_quantity += budget_line.quantity or 0.0
                
                # Sum x_studio_float_field_4nk_1j1fvng8q field
                if hasattr(budget_line, 'x_studio_float_field_4nk_1j1fvng8q'):
                    sul_sawyobi += getattr(budget_line, 'x_studio_float_field_4nk_1j1fvng8q') or 0.0
                quantity += budget_line.quantity or 0.0
            
            # Calculate unit_price and budget_qty_price
            unit_price = 0.0
            budget_qty_price = 0.0
            if quantity > 0:
                unit_price = sul_sawyobi / quantity
                budget_qty_price = budget_quantity * unit_price
            
            # Group by product_id, categ_id, and dep_code, then sum quantities and amounts
            total_quantity = sum(all_matching_lines.mapped('quantity'))
            total_amount = sum(all_matching_lines.mapped('amount'))
            
            # Mark all matched lines red when grouped totals exceed budget
            if total_quantity > budget_quantity or total_amount > budget_qty_price:
                if all_matching_lines and line.id in all_matching_lines.ids:
                    line.exceeds_budget = True
    
    def _check_budget_limits(self):
        """Check if lines exceed budget limits and mark them"""
        # Group lines by product_id and categ_id where request has x_studio_selection_field_6ca_1j76p9boc == 'მარაგები'
        lines_to_check = self.filtered(lambda l: 
            l.request_id and 
            hasattr(l.request_id, 'x_studio_selection_field_6ca_1j76p9boc') and
            l.request_id.x_studio_selection_field_6ca_1j76p9boc == 'მარაგები' and
            l.product_id
        )
        
        if not lines_to_check:
            return
        
        # Group by product_id, categ_id, and dep_code
        product_groups = defaultdict(list)
        for line in lines_to_check:
            dep_code = False
            if line.request_id and hasattr(line.request_id, 'dep_code'):
                dep_code = line.request_id.dep_code
            key = (line.product_id.id, line.product_id.categ_id.id, dep_code)
            product_groups[key].append(line)
        
        # Check each group
        for (product_id, categ_id, dep_code), group_lines in product_groups.items():
            # Get the year from the first line's create_date (all lines in group should have same year logic)
            line_year = group_lines[0].create_date.year if group_lines[0].create_date else fields.Datetime.now().year
            year_start = fields.Datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).replace(year=line_year)
            year_end = fields.Datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).replace(year=line_year + 1)
            
            # Search for budgeting.line with same product_id and categ_id
            # Filter by request_id.request_date.year equal to inventory_line create_date.year
            budgeting_lines = self.env['budgeting.line'].search([
                ('x_studio_related_field_441_1j1fsaqsg', '=', categ_id),
                ('request_id.request_date', '>=', year_start.date()),
                ('request_id.request_date', '<', year_end.date())
            ])
            
            # Get all inventory.request lines with same product_id, categ_id, and dep_code where x_studio_selection_field_6ca_1j76p9boc == 'მარაგები'
            # Filter by create_date.year matching line's create_date.year
            domain = [
                # ('product_id', '=', product_id),
                ('product_id.categ_id', '=', categ_id),
                ('request_id.x_studio_selection_field_6ca_1j76p9boc', '=', 'მარაგები'),
                ('request_id.september_request_ids', '=', False),
                ('create_date', '>=', year_start),
                ('create_date', '<', year_end)
            ]
            # Add dep_code to domain
            if dep_code:
                domain.append(('request_id.dep_code', '=', dep_code))
            else:
                domain.append(('request_id.dep_code', '=', False))
            
            all_matching_lines = self.env['inventory.line'].search(domain)
            
            # If no budgeting_lines found, mark all matching lines as red
            if not budgeting_lines:
                # Trigger recomputation of exceeds_budget for all lines in group
                for line in all_matching_lines:
                    line.invalidate_recordset(['exceeds_budget'])
                continue
            
            # Get budget quantity
            # dep_code is already in the group key from the grouping above
            
            budget_quantity = 0.0
            # Sum x_studio_float_field_4nk_1j1fvng8q from all budgeting lines
            sul_sawyobi = 0.0
            quantity = 0.0
            for budget_line in budgeting_lines:
                field_name = None
                if dep_code == "ცფ":
                    field_name = 'x_studio_float_field_607_1j3r255vi'
                elif dep_code == "ცფს":
                    field_name = 'x_studio_float_field_971_1j3r2i8ah'
                elif dep_code == "კს":
                    field_name = 'x_studio_float_field_3bu_1j3r2insu'
                elif dep_code == "ჩფ":
                    field_name = 'x_studio_float_field_7rg_1j3r2j0fc'
                elif dep_code == "ყუ":
                    field_name = 'x_studio_float_field_1p5_1j3r2j88f'
                elif dep_code == "დფ":
                    field_name = 'x_studio_float_field_349_1j3r2jgm8'
                elif dep_code == "ოდო":
                    field_name = 'x_studio_float_field_366_1j3r2jrui'
                elif dep_code == "მეტ":
                    field_name = 'x_studio_float_field_9r_1j3r2kjpn'
                
                if field_name and hasattr(budget_line, field_name):
                    budget_quantity += getattr(budget_line, field_name) or 0.0
                else:
                    budget_quantity += budget_line.quantity or 0.0
                
                # Sum x_studio_float_field_4nk_1j1fvng8q field
                if hasattr(budget_line, 'x_studio_float_field_4nk_1j1fvng8q'):
                    sul_sawyobi += getattr(budget_line, 'x_studio_float_field_4nk_1j1fvng8q') or 0.0
                quantity += budget_line.quantity

            # Calculate unit_price and budget_qty_price
            unit_price = 0.0
            budget_qty_price = 0.0
            if quantity > 0:
                unit_price = sul_sawyobi / quantity
                budget_qty_price = budget_quantity * unit_price
            
            # Sum total quantity and amount
            total_quantity = sum(all_matching_lines.mapped('quantity'))
            total_amount = sum(all_matching_lines.mapped('amount'))
            
            # If total grouped quantity >= budget, mark the last line (changed from > to >=)
            if total_quantity > budget_quantity or total_amount > budget_qty_price:
                now = fields.Datetime.now()
                sorted_lines = all_matching_lines.sorted(key=lambda l: (l.create_date or now, l.id))
                if sorted_lines:
                    last_line = sorted_lines[-1]
                    # Trigger recomputation of exceeds_budget for all lines in group
                    for line in all_matching_lines:
                        line.invalidate_recordset(['exceeds_budget'])

    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-set budget_analytic_line"""
        records = super(InventoryLine, self).create(vals_list)
        if records:
            records._check_budget_limits()
            # NEW: Auto-set budget_analytic_line for non-red lines
            records._auto_set_budget_analytic_line()
        return records
    
    def write(self, vals):
        """Override write to auto-set budget_analytic_line"""
        result = super(InventoryLine, self).write(vals)
        if any(field in vals for field in ['quantity', 'product_id']):
            self._check_budget_limits()
            # NEW: Auto-set budget_analytic_line for non-red lines
            if 'budget_analytic_line' not in vals:
                self._auto_set_budget_analytic_line()
        return result
    
    def _auto_set_budget_analytic_line(self):
        """
        AUTO-FILL budget_analytic_line when line is NOT red (exceeds_budget = False)
        
        Simple logic:
        1. Check if line is red (exceeds budget)
        2. If NOT red → find matching budgeting.line
        3. Set budget_analytic_line from budgeting.line
        """
        for line in self:
            # Skip if not 'მარაგები' request
            if not line.request_id or not line.product_id:
                continue
            
            request = line.request_id
            if not hasattr(request, 'x_studio_selection_field_6ca_1j76p9boc'):
                continue
            
            if request.x_studio_selection_field_6ca_1j76p9boc != 'მარაგები':
                continue
            
            # Skip if budget_analytic_line is already set
            if line.budget_analytic_line:
                continue
            
            # Check if line is red (exceeds budget)
            if line.exceeds_budget:
                _logger.info(f"Line {line.id} exceeds budget - skipping auto-set")
                continue
            
            # ✅ Line is NOT red - let's auto-fill budget_analytic_line
            
            # Get department code
            dep_code = False
            if hasattr(request, 'dep_code'):
                dep_code = request.dep_code
            
            # Get year
            line_year = line.create_date.year if line.create_date else fields.Datetime.now().year
            year_start = fields.Datetime.now().replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            ).replace(year=line_year)
            year_end = year_start.replace(year=line_year + 1)
            
            # Find matching budgeting.line (same category, same year)
            budgeting_lines = self.env['budgeting.line'].search([
                ('x_studio_related_field_441_1j1fsaqsg', '=', line.product_id.categ_id.id),
                ('request_id.request_date', '>=', year_start.date()),
                ('request_id.request_date', '<', year_end.date())
            ])
            
            if not budgeting_lines:
                _logger.info(f"No budgeting.line found for line {line.id}")
                continue
            
            # Get the budget_analytic_line from budgeting.line
            # You can choose which budgeting.line to use:
            # Option 1: Use the first one
            budget_line = budgeting_lines[0]
            
            # Check if budgeting.line has budget_analytic_line field
            if hasattr(budget_line, 'budget_analytic_line') and budget_line.budget_analytic_line:
                line.budget_analytic_line = budget_line.budget_analytic_line
                _logger.info(
                    f"✅ Auto-set budget_analytic_line = {budget_line.budget_analytic_line.id} "
                    f"for line {line.id} (product: {line.product_id.name})"
                )
            else:
                _logger.info(f"No budget_analytic_line found in budgeting.line {budget_line.id}")

    def action_compute_update_unit_price(self):
        for rec in self:
            if not rec.x_studio_purchase and rec.unit_price == 0.0:
                rec.unit_price = rec.product_id.standard_price
