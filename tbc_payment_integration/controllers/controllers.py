# -*- coding: utf-8 -*-
# from odoo import http


# class TbcPaymentIntegration(http.Controller):
#     @http.route('/tbc_payment_integration/tbc_payment_integration', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/tbc_payment_integration/tbc_payment_integration/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('tbc_payment_integration.listing', {
#             'root': '/tbc_payment_integration/tbc_payment_integration',
#             'objects': http.request.env['tbc_payment_integration.tbc_payment_integration'].search([]),
#         })

#     @http.route('/tbc_payment_integration/tbc_payment_integration/objects/<model("tbc_payment_integration.tbc_payment_integration"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('tbc_payment_integration.object', {
#             'object': obj
#         })

