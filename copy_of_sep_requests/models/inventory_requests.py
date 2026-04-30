from odoo import models, fields, api

class SeptemberRequest(models.Model):
    _inherit = "september.request"


    def copy_to_inventory(self):
        """Called by server action"""
        for rec in self:
            inventory_request = self.env["inventory.request"].create({
                "name": rec.name,
                "request_date": rec.request_date,
                "x_studio_request_number" : rec.x_studio_request_number,
                "priority": rec.priority,
                "description" : rec.description,
                "requested_by": rec.requested_by.id if rec.requested_by else False,
                "department_id": rec.x_studio_department.id if rec.x_studio_department else False,
            })

        return True
