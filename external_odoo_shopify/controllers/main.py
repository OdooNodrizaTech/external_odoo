# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request


class ExternalSaleOrderShopifyController(http.Controller):

    @http.route(['/external_sale_order/shopify/action_run'],
                type='http',
                auth='public',
                methods=['GET'],
                website=True
                )
    def external_sale_order_shopify_action_run(self, **get):
        request.env['external.sale.order'].sudo().cron_sqs_external_sale_order_shopify()
        return request.render('website.404')

    @http.route(['/shopify_permission'],
                type='http',
                auth='public',
                methods=['GET'],
                website=True
                )
    def shopify_permission(self, **get):
        if 'code' in get:
            if 'shop' in get:
                items = request.env['external.source'].sudo().search(
                    [
                        ('type', '=', 'shopify'),
                        ('url', '=', str(get['shop']))
                    ]
                )
                if items:
                    # shopify_request_token
                    items[0].shopify_request_token({
                        'code': str(get['code']),
                        'hmac': str(get['hmac']),
                        'shop': str(get['shop']),
                        'timestamp': str(get['timestamp'])
                    })
        # return
        return request.render('website.404')
