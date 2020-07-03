# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class ExternalSaleOrderShopifyController(http.Controller):

    @http.route(['/external_sale_order/shopify/action_run'], type='http', auth='public', methods=['GET'], website=True)
    def external_sale_order_shopify_action_run(self, **get):
        _logger.info('external_sale_order_shopify_action_run (controller)')
        request.env['external.sale.order'].sudo().cron_sqs_external_sale_order_shopify()
        return request.render('website.404')
        
    @http.route(['/shopify_permission'], type='http', auth='public', methods=['GET'], website=True)
    def shopify_permission(self, **get):
        #save_shopify_code
        if 'code' in get:
            if 'shop' in get:
                external_source_ids = request.env['external.source'].sudo().search([('type', '=', 'shopify'),('url', '=', str(get['shop']))])
                if len(external_source_ids)>0:
                    external_source_id = external_source_ids[0]
                    #shopify_request_token
                    external_source_id.shopify_request_token({
                        'code': str(get['code']),
                        'hmac': str(get['hmac']),
                        'shop': str(get['shop']),
                        'timestamp': str(get['timestamp'])
                    })                    
        #return
        return request.render('website.404')        