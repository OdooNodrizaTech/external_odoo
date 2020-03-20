# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class ExternalSaleOrderShopifyController(http.Controller):

    @http.route(['/external_sale_order/shopify/action_run'], type='http', auth='public', methods=['GET'], website=True)
    def external_sale_order_shopify_action_run(self, **post):
        _logger.info('external_sale_order_shopify_action_run (controller)')
        request.env['external.sale.order'].sudo().cron_sqs_external_sale_order_shopify()
        return request.render('website.404')