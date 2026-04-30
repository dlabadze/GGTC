from odoo import api, fields, models

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    count_calendar_days = fields.Boolean(
        string='კალენდარული დღეები',
        help='მონიშნეთ თუ გსურთ რომ ამ ტიპისთვის დაითვალოს ყველა კალენდარული დღე (შაბათ-კვირის ჩათვლით)',
        default=False
    )

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = super(HrLeave, self)._get_durations(check_leave_type, resource_calendar)
        
        for leave in self:
            is_biuleteni = False
            if leave.holiday_status_id:
                if getattr(leave.holiday_status_id, 'id', 0) == 2 or getattr(leave.holiday_status_id, 'count_calendar_days', False):
                    is_biuleteni = True
                
                name = getattr(leave.holiday_status_id, 'name', '')
                if name and 'ბიულ' in name:
                    is_biuleteni = True
            
            if is_biuleteni and leave.request_date_from and leave.request_date_to:
                delta = (leave.request_date_to - leave.request_date_from).days
                days = max(delta + 1, 0)
                hours = days * 8  # Standard hours per day approximation
                
                # Check if it's already in the result dict, if not add it
                # Fallback to id if it's stored, otherwise use new ID
                result[leave.id] = (days, hours)
                
        return result
