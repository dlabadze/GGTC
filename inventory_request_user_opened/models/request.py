from odoo import models, fields
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)



class Request(models.Model):
    _inherit = 'inventory.request'

    is_opened = fields.Boolean(string='Is Opened', default=False)
    see_status_message = fields.Char(string='User Opened Message', default='')