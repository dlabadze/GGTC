from odoo import models, api, fields
from collections import defaultdict


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    WEEKEND_INCLUSIVE_TYPES = ['მივლინება', 'ბიულეტენი', 'დეკრეტული შვებულება', 'მძიმე, მავნე და საშიშპირობებიანი შვებულება']

    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _compute_duration(self):
        if hasattr(super(), '_compute_duration'):
            super()._compute_duration()
        for leave in self:
            if leave.date_from and leave.date_to:
                if leave.holiday_status_id and leave.holiday_status_id.name in self.WEEKEND_INCLUSIVE_TYPES:
                    days = self._calculate_days_including_weekends(leave.date_from, leave.date_to)
                    leave.number_of_days = days
                    if hasattr(leave, 'duration_display'):
                        leave.duration_display = f"{days} days"

    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _compute_duration_display(self):
        if hasattr(super(), '_compute_duration_display'):
            super()._compute_duration_display()
        for leave in self:
            if leave.date_from and leave.date_to:
                if leave.holiday_status_id and leave.holiday_status_id.name in self.WEEKEND_INCLUSIVE_TYPES:
                    days = self._calculate_days_including_weekends(leave.date_from, leave.date_to)
                    leave.duration_display = f"{days} days"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._adjust_vals_for_business_trip(vals)
        return super().create(vals_list)

    def write(self, vals):
        # Separate records that need a custom number_of_days from those that don't.
        # Key insight: group by the overridden day count so we can batch write
        # each group in ONE call — avoids mid-loop constraint violations.

        # Map: number_of_days value → recordset that needs it
        grouped = defaultdict(lambda: self.env['hr.leave'])
        normal = self.env['hr.leave']

        for leave in self:
            # We must pass a copy of vals since _adjust_vals_for_business_trip modifies it
            adjusted_vals = leave._adjust_vals_for_business_trip(dict(vals))
            overridden_days = adjusted_vals.get('number_of_days')
            original_days = vals.get('number_of_days')

            if overridden_days is not None and overridden_days != original_days:
                grouped[overridden_days] |= leave
            else:
                normal |= leave

        # Write each group as a single batched call
        for days, records in grouped.items():
            batch_vals = dict(vals)
            batch_vals['number_of_days'] = days
            super(HrLeave, records).write(batch_vals)

        if normal:
            super(HrLeave, normal).write(vals)

        return True

    def _adjust_vals_for_business_trip(self, vals):
        date_from = vals.get('date_from') or self.date_from
        date_to = vals.get('date_to') or self.date_to
        holiday_status_id = vals.get('holiday_status_id') or self.holiday_status_id.id

        leave_type = (
            self.env['hr.leave.type'].browse(holiday_status_id)
            if holiday_status_id else None
        )

        if date_from and date_to and leave_type and leave_type.name in self.WEEKEND_INCLUSIVE_TYPES:
            days = self._calculate_days_including_weekends(date_from, date_to)
            vals['number_of_days'] = days

        return vals

    def _calculate_days_including_weekends(self, date_from, date_to):
        if isinstance(date_from, str):
            date_from = fields.Datetime.from_string(date_from).date()
        else:
            date_from = date_from.date()

        if isinstance(date_to, str):
            date_to = fields.Datetime.from_string(date_to).date()
        else:
            date_to = date_to.date()

        delta = date_to - date_from
        return delta.days + 1 if delta.days >= 0 else 0