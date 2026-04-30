from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class OperationsAutoNumber(models.Model):
    _inherit = 'x_operations'
    
    # BULLETPROOF SEQUENCE FIELD - Studio Compatible
    x_operation_number = fields.Char(
        string='Operation Number',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
        placeholder='ავტომატური ნომერი',
        index=True  # Better performance
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """BULLETPROOF create method - handles Studio and custom module"""
        for vals in vals_list:
            # Generate sequence if not provided or is 'New'
            if (vals.get('x_operation_number', 'New') == 'New' or
                    not vals.get('x_operation_number')):
                vals['x_operation_number'] = self._generate_operation_number()
                
                # Log for debugging
                _logger.info(
                    f"Generated operation sequence: "
                    f"{vals['x_operation_number']}"
                )
        
        return super(OperationsAutoNumber, self).create(vals_list)
    
    def _generate_operation_number(self):
        """BULLETPROOF sequence generation with yearly reset"""
        current_year = fields.Date.today().year
        
        # Use database query for better performance and reliability
        self.env.cr.execute("""
            SELECT COUNT(*) 
            FROM x_operations 
            WHERE create_date >= %s 
            AND create_date < %s 
            AND x_operation_number != 'New' 
            AND x_operation_number IS NOT NULL
            AND x_operation_number != ''
        """, (f'{current_year}-01-01', f'{current_year + 1}-01-01'))
        
        count = self.env.cr.fetchone()[0]
        next_number = count + 1
        
        # Format: N/1 (e.g., 1/1, 2/1, 3/1...)
        sequence = f"{next_number}/1"
        
        _logger.info(
            f"Generated operation sequence {sequence} for year "
            f"{current_year}"
        )
        return sequence
