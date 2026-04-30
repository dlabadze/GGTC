from . import models

def post_init_hook(cr, registry):
    """Post-install script"""
    # Force registration of all models
    from odoo.modules.module import load_openerp_module
    load_openerp_module('salary_management')