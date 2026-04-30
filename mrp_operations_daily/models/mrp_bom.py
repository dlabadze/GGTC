from odoo import models, fields, api
from datetime import date
from collections import defaultdict
from dateutil.relativedelta import relativedelta


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    priority_number = fields.Integer(string='Priority')
    quantity_for_daily = fields.Float(string='Quantity for Daily')

    @api.model
    def create_daily_operations(self):
        """
        Scheduled action method to create daily Manufacturing Orders from BOMs.
        Groups BOMs by code, sorts by priority_number, and creates productions progressively.
        
        Day 1: Create production for priority 1
        Day 2: Create productions for priorities 1 and 2
        Day 3: Create productions for priorities 1, 2, and 3
        And so on...
        When all priorities have productions, start over from priority 1.
        """
        today = date.today()
        Production = self.env['mrp.production']
        
        # Get all active BOMs with code and priority_number
        boms = self.search([
            ('active', '=', True),
            ('code', '!=', False),
            ('priority_number', '>', 0)
        ])
        
        if not boms:
            return
        
        # Group BOMs by code
        bom_groups = defaultdict(list)
        for bom in boms:
            bom_groups[bom.code].append(bom)
        
        # Process each group
        for code, group_boms in bom_groups.items():
            # Sort by priority_number (ascending: 1, 2, 3, ...)
            sorted_boms = sorted(group_boms, key=lambda b: b.priority_number)
            if not sorted_boms:
                continue
            
            # Get all priorities for this code
            all_priorities = [bom.priority_number for bom in sorted_boms]
            max_priority = max(all_priorities)
            
            # Check existing productions for this code (product_code) from today
            today_start = fields.Datetime.to_datetime(today)
            today_end = today_start + relativedelta(days=1)
            
            # Get productions created today for this code
            today_productions = Production.search([
                ('product_code', '=', code),
                ('date_start', '>=', today_start),
                ('date_start', '<', today_end),
                ('state', '!=', 'cancel')
            ])
            
            # Get all existing productions for this code (any date)
            all_existing_productions = Production.search([
                ('product_code', '=', code),
                ('state', '!=', 'cancel')
            ])
            
            # Get priorities that have productions (from any date)
            existing_priorities = set()
            for prod in all_existing_productions:
                # Get priority from BOM if available
                if prod.bom_id and prod.bom_id.priority_number:
                    existing_priorities.add(prod.bom_id.priority_number)
            
            # Check if all priorities have productions
            all_priorities_set = set(all_priorities)
            if existing_priorities.issuperset(all_priorities_set):
                # All priorities have productions, reset and start from 1
                # This means we've completed a full cycle, start over
                target_priority = 1
            else:
                # Find the highest consecutive priority that has a production
                # We need to find how many consecutive priorities starting from 1 have productions
                consecutive_count = 0
                for priority in sorted(all_priorities):
                    if priority in existing_priorities:
                        consecutive_count += 1
                    else:
                        break
                # Next day should create up to consecutive_count + 1
                target_priority = consecutive_count + 1
            
            # Create productions for priorities 1 through target_priority
            priorities_to_create = [p for p in sorted(all_priorities) if p <= target_priority]
            
            # Filter out priorities that already have productions created today
            today_priorities = set()
            for prod in today_productions:
                if prod.bom_id and prod.bom_id.priority_number:
                    today_priorities.add(prod.bom_id.priority_number)
            
            # Only create for priorities that don't have productions today
            priorities_to_create = [p for p in priorities_to_create if p not in today_priorities]
            
            # Create productions for priorities that need to be created today
            for priority in priorities_to_create:
                bom = next((b for b in sorted_boms if b.priority_number == priority), None)
                if not bom:
                    continue
                
                self._create_production_from_bom(bom, code, today)
    
    def _create_production_from_bom(self, bom, code, date_today):
        """Helper method to create a Manufacturing Order from a BOM"""
        from datetime import datetime
        
        Production = self.env['mrp.production']
        quantity = bom.quantity_for_daily or bom.product_qty
        
        # Get product from BOM - BOM has product_tmpl_id, get the first variant
        if not bom.product_tmpl_id:
            return
        
        # Get the product variant - if product_id is set, use it, otherwise use first variant
        if bom.product_id:
            product = bom.product_id
        else:
            # Get the first product variant from the template
            product = bom.product_tmpl_id.product_variant_id
            if not product:
                return
        
        # Create production order
        production_vals = {
            'product_id': product.id,
            'bom_id': bom.id,
            'product_qty': quantity,
            'product_uom_id': bom.product_uom_id.id,
            'product_code': code,  # Set the product_code field
            'date_start': datetime.combine(date_today, datetime.min.time()),
            'company_id': bom.company_id.id,
        }
        
        # Get picking type from BOM or use default
        if bom.picking_type_id:
            production_vals['picking_type_id'] = bom.picking_type_id.id
        
        production = Production.create(production_vals)
        
        # Confirm the production order
        try:
            production.action_confirm()
        except Exception:
            # If confirmation fails, leave it in draft
            pass
        
        return production
           