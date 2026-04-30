from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class HrJob(models.Model):
    _inherit = 'hr.job'

    def write(self, vals):
        fields_to_track = ['expected_salary', 'date_contract']
        #x_studio_monetary_field_7gl_1iu13c1vu to expected_salary and x_studio_date_contract to date_contract have to be renamed
        for record in self:
            changes = []
            try:
                for field in fields_to_track:

                    if field in vals and field in record._fields:
                        old_val = record[field]
                        new_val = vals[field]
                        if old_val != new_val:
                            label = record._fields[field].string or field
                            changes.append(f"{label}: {old_val}  \n")
            except Exception as e:
                _logger.error("Error while tracking hr.job changes: %s", e)

            if changes:
                try:
                    message = "შეცვლილია: " + " ".join(changes)
                    record.message_post(body=message, subtype_xmlid="mail.mt_note")
                except Exception as e:
                    _logger.error("Error posting message to hr.job chatter: %s", e)

        return super(HrJob, self).write(vals)
