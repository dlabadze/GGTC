from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def get_invoice_series_number(self, factura_num, rs_acc, rs_pass):
        """
        Get invoice f_series and f_number from faqtura system and return combined string.
        Returns the combined value like "ეა-84 4984931" to compare with get_invoice_id.
        Uses the existing get_invoice method and parses the result.
        """
        # Use the existing get_invoice method which already has all the proper inheritance
        # It returns the combined string like "ეა-84 4984931"
        account_move_model = self.env['account.move']
        
        # Call the existing get_invoice method which is already defined in extension_views
        f_complete = account_move_model.get_invoice(factura_num, rs_acc, rs_pass)
        
        _logger.info(f'✅ Invoice retrieved: {f_complete} for factura_num: {factura_num}')
        
        return f_complete

    def action_check_factura_numbers(self):
        """
        Check selected account.move records and update f_series and f_number
        in their related combined_invoice_id if they differ.
        """
        if not self:
            raise UserError("გთხოვთ აირჩიოთ ინვოისები შემოწმებისთვის")
        
        # Get user credentials
        user = self.env.user
        rs_acc = user.rs_acc
        rs_pass = user.rs_pass
        
        if not rs_acc or not rs_pass:
            raise UserError("გთხოვთ შეავსოთ rs.ge ექაუნთი და პაროლი მომხმარებლის პარამეტრებში")
        
        updated_count = 0
        error_count = 0
        no_change_count = 0
        errors = []
        
        for move in self:
            try:
                # Check if move has combined_invoice_id
                if not move.combined_invoice_id:
                    continue
                
                combined_invoice = move.combined_invoice_id
                
                # Check if factura_num exists
                if not combined_invoice.factura_num:
                    continue
                
                # Get combined f_series and f_number from API (like "ეა-84 4984931")
                new_get_invoice_id = self.get_invoice_series_number(
                    combined_invoice.factura_num,
                    rs_acc,
                    rs_pass
                )
                
                # Compare with stored value in get_invoice_id
                current_get_invoice_id = combined_invoice.get_invoice_id or ''
                
                # Check if values differ
                if new_get_invoice_id != current_get_invoice_id:
                    # Update the combined invoice
                    combined_invoice.write({
                        'get_invoice_id': new_get_invoice_id,
                    })
                    updated_count += 1
                    _logger.info(f'Updated invoice {move.name}: get_invoice_id={new_get_invoice_id}')
                else:
                    no_change_count += 1
                    
            except Exception as e:
                error_count += 1
                error_msg = f"შეცდომა ინვოისზე {move.name}: {str(e)}"
                errors.append(error_msg)
                _logger.error(error_msg)
        
        # Prepare result message
        messages = []
        if updated_count > 0:
            messages.append(f"განახლებულია {updated_count} ინვოისი")
        if no_change_count > 0:
            messages.append(f"ცვლილება არ იყო საჭირო {no_change_count} ინვოისზე")
        if error_count > 0:
            messages.append(f"შეცდომა {error_count} ინვოისზე")
        
        if messages:
            message = "\n".join(messages)
            if error_count > 0:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'შედეგი',
                        'message': message,
                        'type': 'warning',
                        'sticky': True,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'შედეგი',
                        'message': message,
                        'type': 'success',
                        'sticky': False,
                    }
                }
        else:
            raise UserError("არცერთ ინვოისს არ აქვს დაკავშირებული combined invoice ან factura_num")

