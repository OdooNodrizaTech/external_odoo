# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import http
from odoo.http import request


class ExternalSaleOrderWoocommerceController(http.Controller):

    @http.route(['/external_sale_order/woocommerce/action_run'],
                type='http',
                auth='public',
                methods=['GET'],
                website=True
                )
    def external_sale_order_woocommerce_action_run(self, **post):
        request.env[
            'external.sale.order'
        ].sudo().cron_sqs_external_sale_order_woocommerce()
        return request.render('website.404')

    @http.route(['/external_stock_picking/woocommerce/action_run'],
                type='http',
                auth='public',
                methods=['GET'],
                website=True
                )
    def external_stock_picking_woocommerce_action_run(self, **post):
        request.env[
            'external.stock.picking'
        ].sudo().cron_sqs_external_stock_picking_woocommerce()
        return request.render('website.404')
