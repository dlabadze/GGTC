# biuleteni_out_contract_fix/models/hr_payslip.py
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        Fix: when computing out-of-contract days, don't count public holidays
        that are defined on the resource calendar as working days.

        We call super() with check_out_of_contract=False to get the normal
        worked days, then we recompute the OUT_OF_CONTRACT line ourselves
        using compute_leaves=True so calendar leaves are excluded.
        """
        self.ensure_one()

        # 1) Let standard logic compute the "normal" worked days
        res = super(HrPayslip, self)._get_worked_day_lines(
            domain=domain, check_out_of_contract=False
        )

        # If we are not supposed to add out-of-contract lines, just return
        if not check_out_of_contract:
            return res

        contract = self.contract_id
        if not contract or not contract.resource_calendar_id:
            return res

        out_days = 0.0
        out_hours = 0.0

        reference_calendar = self._get_out_of_contract_calendar()

        # Domain: include only non-leave work intervals
        work_domain = [
            "|",
            ("work_entry_type_id", "=", False),
            ("work_entry_type_id.is_leave", "=", False),
        ]

        # 2) Before contract start, inside payslip period
        if self.date_from < contract.date_start:
            start = fields.Datetime.to_datetime(self.date_from)
            stop = (
                fields.Datetime.to_datetime(contract.date_start)
                + relativedelta(days=-1, hour=23, minute=59)
            )
            if start <= stop:
                # compute_leaves=True so public holidays (calendar leaves)
                # are taken into account, then we filter out leaves with domain
                out_time = reference_calendar.get_work_duration_data(
                    start,
                    stop,
                    compute_leaves=True,
                    domain=work_domain,
                )
                out_days += out_time.get("days", 0.0)
                out_hours += out_time.get("hours", 0.0)

        # 3) After contract end, inside payslip period
        if contract.date_end and contract.date_end < self.date_to:
            start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(
                days=1
            )
            stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(
                hour=23, minute=59
            )
            if start <= stop:
                out_time = reference_calendar.get_work_duration_data(
                    start,
                    stop,
                    compute_leaves=True,
                    domain=work_domain,
                )
                out_days += out_time.get("days", 0.0)
                out_hours += out_time.get("hours", 0.0)

        # 4) Create / append OUT_OF_CONTRACT line if any time exists
        if out_days or out_hours:
            work_entry_type = self.env.ref("hr_payroll.hr_work_entry_type_out_of_contract")
            res.append(
                {
                    "sequence": work_entry_type.sequence,
                    "work_entry_type_id": work_entry_type.id,
                    "number_of_days": out_days,
                    "number_of_hours": out_hours,
                }
            )

        return res
