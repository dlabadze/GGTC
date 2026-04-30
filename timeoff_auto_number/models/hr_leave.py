# models/hr_leave.py - FIXED VERSION
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class HrLeave(models.Model):
    _inherit = 'hr.leave'
    
    nomeri = fields.Char(
        string='ნომერი',
        readonly=True,
        copy=False,
        help='Automatic sequential number for time off request'
    )
    
    @api.model
    def create(self, vals):
        """Override create to add automatic sequential numbers"""
        if not vals.get('nomeri'):
            vals['nomeri'] = self._generate_next_number()
        
        record = super().create(vals)
        _logger.info(f"✅ Created Time Off request with ნომერი: {record.nomeri}")
        return record
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add automatic sequential numbers"""
        for vals in vals_list:
            if not vals.get('nomeri'):
                vals['nomeri'] = self._generate_next_number()
        
        records = super().create(vals_list)
        
        for record in records:
            _logger.info(f"✅ Created Time Off request with ნომერი: {record.nomeri}")
        
        return records
    
    @api.model
    def default_get(self, fields_list):
        """FIXED: Set ნომერი immediately when form opens"""
        defaults = super().default_get(fields_list)
        
        # If nomeri is in the requested fields, generate it immediately
        if 'nomeri' in fields_list:
            defaults['nomeri'] = self._generate_next_number()
            _logger.info(f"🔢 Generated ნომერი for new form: {defaults['nomeri']}")
        
        return defaults
    
    def _generate_next_number(self):
        """Generate next sequential 5-digit number"""
        try:
            # Find the highest existing number using SQL for better performance
            self.env.cr.execute("""
                SELECT COALESCE(MAX(CAST(nomeri AS INTEGER)), 0) 
                FROM hr_leave 
                WHERE nomeri IS NOT NULL 
                AND nomeri ~ '^[0-9]+$'
            """)
            
            result = self.env.cr.fetchone()
            last_number = result[0] if result else 0
            next_number = last_number + 1
            
            # Format as 5-digit number with leading zeros
            formatted_number = f"{next_number:05d}"
            
            _logger.info(f"🔢 Generated next ნომერი: {formatted_number}")
            return formatted_number
            
        except Exception as e:
            _logger.error(f"❌ Error generating number: {str(e)}")
            # Fallback: use ORM
            try:
                records = self.search([('nomeri', '!=', False)])
                if records:
                    numbers = []
                    for record in records:
                        try:
                            if record.nomeri and record.nomeri.isdigit():
                                numbers.append(int(record.nomeri))
                        except:
                            continue
                    
                    next_number = max(numbers) + 1 if numbers else 1
                else:
                    next_number = 1
                
                return f"{next_number:05d}"
                
            except:
                # Final fallback - use timestamp
                import time
                return f"{int(time.time()) % 100000:05d}"