# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from odoo import api, fields, models, tools, _

from dateutil.relativedelta import relativedelta
from datetime import datetime
import dateutil.parser
import pytz
from woocommerce import API
_logger = logging.getLogger(__name__)


class ExternalSource(models.Model):
    _inherit = 'external.source'

    @api.multi
    def generate_external_sale_order_woocommerce(self, vals):
        # result_message
        result_message = {
            'statusCode': 200,
            'return_body': 'OK',
            'delete_message': False,
            'message': vals
        }
        # external_sale_order
        order_vals = {
            'external_id': str(vals['id']),
            'external_source_id': self.id,
            'woocommerce_state': str(vals['status']),
            'number': str(vals['number']),
            'total_price': str(vals['total']),
            'total_tax': str(vals['total_tax']),
            'total_discounts': str(vals['discount_total'])
        }
        # Fix date
        date_created = dateutil.parser.parse(str(vals['date_created']))
        order_vals['date'] = date_created.strftime("%Y-%m-%d %H:%M:%S")
        # currency
        items = self.env['res.currency'].sudo().search(
            [
                ('name', '=', str(vals['currency']))
            ]
        )
        if items:
            order_vals['currency_id'] = items[0].id
        # external_customer
        customer_vals = {
            'external_source_id': self.id,
            'active': True,
            'external_id': int(vals['customer_id']),
            'province_code': str(vals['shipping']['state']),
            'country_code': str(vals['shipping']['country'])
        }
        # vat colocarlo bien aqui y en la direccion de facturacion
        if 'meta_data' in vals:
            for meta_data_item in vals['meta_data']:
                if meta_data_item['key'] == 'NIF':
                    customer_vals['vat'] = str(meta_data_item['value'])
                    # fields_billing
        fields_billing = ['email', 'phone']
        for field_billing in fields_billing:
            if field_billing in vals['billing']:
                if vals['billing'][field_billing] != '':
                    customer_vals[field_billing] = str(vals['billing'][field_billing])
                    # fields_shipping
        fields_shipping = [
            'first_name', 'last_name', 'company', 'address_1',
            'address_2', 'city', 'postcode'
        ]
        for field_shipping in fields_shipping:
            if field_shipping in vals['shipping']:
                if vals['shipping'][field_shipping] != '':
                    customer_vals[field_shipping] = str(vals['shipping'][field_shipping])
        # fix external_id=0
        if customer_vals['external_id'] == 0:
            if 'email' in external_customer_vals:
                customer_vals['external_id'] = str(customer_vals['email'])
        # search_previous
        items = self.env['external.customer'].sudo().search(
            [
                ('external_source_id', '=', self.id),
                ('external_id', '=', str(vals['customer_id']))
            ]
        )
        if items:
            customer_obj = items[0]
        else:
            # create
            customer_obj = self.env['external.customer'].sudo(6).create(
                customer_vals
            )
        # define
        order_vals['external_customer_id'] = customer_obj.id
        # external_address
        address_types = ['billing', 'shipping']
        for address_type in address_types:
            # vals
            address_vals = {
                'external_id': order_vals['external_id'],
                'external_customer_id': external_customer_obj.id,
                'external_source_id': self.id,
                'type': 'invoice'
            }
            # address_fields_need_check
            address_fields_need_check = [
                'first_name', 'last_name', 'company', 'address_1',
                'address_2', 'city', 'state', 'postcode', 'country',
                'phone'
            ]
            for field_need_check in address_fields_need_check:
                if field_need_check in vals[address_type]:
                    if vals[address_type][field_need_check] != '':
                        if vals[address_type][field_need_check] is not None:
                            address_vals[field_need_check] = str(
                                vals[address_type][field_need_check])
            # replace address_1
            if 'address_1' in address_vals:
                address_vals['address1'] = address_vals['address_1']
                del address_vals['address_1']
            # replace address_2
            if 'address_2' in address_vals:
                address_vals['address2'] = address_vals['address_2']
                del address_vals['address_2']
            # replace state
            if 'state' in address_vals:
                address_vals['province_code'] = address_vals['state']
                del address_vals['state']
            # replace country
            if 'country' in address_vals:
                address_vals['country_code'] = address_vals['country']
                del address_vals['country']
                # type
            if address_type == 'shipping':
                address_vals['type'] = 'delivery'
            # fix_external_address_vals
            address_vals['external_id'] += '_' + str(address_vals['type'])
            # search_previous
            items = self.env['external.address'].sudo().search(
                [
                    ('external_source_id', '=', self.id),
                    ('external_customer_id', '=', address_vals['external_customer_id']),
                    ('external_id', '=', address_vals['external_id']),
                    ('type', '=', address_vals['type'])
                ]
            )
            if items:
                address_obj = items[0]
            else:
                # create
                address_obj = self.env['external.address'].sudo(6).create(address_vals)
            # define address_id
            if address_type == 'billing':
                order_vals['external_billing_address_id'] = address_obj.id
            else:
                order_vals['external_shipping_address_id'] = address_obj.id
        # external_sale_order
        _logger.info(order_vals)
        items = self.env['external.sale.order'].sudo().search(
            [
                ('external_source_id', '=', self.id),
                ('external_id', '=', str(order_vals['external_id']))
            ]
        )
        if items:
            order_obj = items[0]
            order_obj.woocommerce_state = str(vals['status'])
            # action_run (only if need)
            order_obj.action_run()
            # result_message
            result_message['delete_message'] = True
            result_message['return_body'] = {
                'message': _('As it already exists, we update its status only')
            }
        else:
            # create
            order_obj = self.env['external.sale.order'].sudo(6).create(order_vals)
            # update subtotal_price
            order_obj.subtotal_price = order_obj.total_price - order_obj.total_tax
            # line_items
            for line_item in vals['line_items']:
                # vals
                line_vals = {
                    'line_id': str(line_item['id']),
                    'external_id': str(line_item['product_id']),
                    'external_sale_order_id': order_obj.id,
                    'currency_id': order_obj.currency_id.id,
                    'sku': str(line_item['sku']),
                    'title': str(line_item['name']),
                    'quantity': int(line_item['quantity']),
                    'price': line_item['price'],
                    'tax_amount': line_item['total_tax']
                }
                # variation_id
                if 'variation_id' in line_item:
                    if line_item['variation_id'] != '':
                        line_vals['external_variant_id'] = str(line_item['variation_id'])
                # create
                self.env['external.sale.order.line'].sudo(6).create(line_vals)
            # shipping_lines
            for shipping_line in vals['shipping_lines']:
                # vals
                shipping_vals = {
                    'external_id': str(shipping_line['id']),
                    'currency_id': order_obj.currency_id.id,
                    'external_sale_order_id': order_obj.id,
                    'title': str(shipping_line['method_title']),
                    'price': shipping_line['total'],
                    'tax_amount': shipping_line['total_tax']
                }
                # create
                self.env['external.sale.order.shipping'].sudo(6).create(shipping_vals)
            # action_run
            order_obj.action_run()
            # delete_message
            result_message['delete_message'] = True
        # return
        return result_message

    @api.multi
    def generate_external_stock_picking_woocommerce(self, vals):
        # result_message
        result_message = {
            'statusCode': 200,
            'return_body': 'OK',
            'delete_message': False,
            'message': vals
        }
        # external_customer
        customer_vals = {
            'external_source_id': self.id,
            'active': True,
            'external_id': int(vals['customer_id']),
            'province_code': str(vals['shipping']['state']),
            'country_code': str(vals['shipping']['country'])
        }
        # vat
        if 'meta_data' in vals:
            for meta_data_item in vals['meta_data']:
                if meta_data_item['key'] == 'NIF':
                    customer_vals['vat'] = str(meta_data_item['value'])
                    # fields_billing
        fields_billing = ['email', 'phone']
        for field_billing in fields_billing:
            if field_billing in vals['billing']:
                if vals['billing'][field_billing] != '':
                    customer_vals[field_billing] = str(vals['billing'][field_billing])
                    # fields_shipping
        fields_shipping = [
            'first_name', 'last_name', 'company',
            'address_1', 'address_2', 'city', 'postcode'
        ]
        for field_shipping in fields_shipping:
            if field_shipping in vals['shipping']:
                if vals['shipping'][field_shipping] != '':
                    customer_vals[field_shipping] = str(vals['shipping'][field_shipping])
        # fix external_id=0
        if customer_vals['external_id'] == 0:
            if 'email' in customer_vals:
                customer_vals['external_id'] = str(customer_vals['email'])
        # search_previous
        items = self.env['external.customer'].sudo().search(
            [
                ('external_source_id', '=', self.id),
                ('external_id', '=', str(external_customer_vals['external_id']))
            ]
        )
        if items:
            customer_obj = items[0]
        else:
            # create
            customer_obj = self.env['external.customer'].sudo(6).create(
                customer_vals
            )
        # external_stock_picking
        picking_vals = {
            'external_id': str(vals['id']),
            'external_customer_id': customer_obj.id,
            'external_source_id': self.id,
            'woocommerce_state': str(vals['status']),
            'number': str(vals['number']),
            'external_source_name': 'web'
        }
        # search_previous
        items = self.env['external.stock.picking'].sudo().search(
            [
                ('external_id', '=', str(picking_vals['external_id'])),
                ('external_source_id', '=', self.id)
            ]
        )
        if items:
            picking_obj = items[0]
            picking_obj.woocommerce_state = str(vals['status'])
            # action_run (only if need)
            picking_obj.action_run()
            # result_message
            result_message['delete_message'] = True
            result_message['return_body'] = {
                'message': _('As it already exists, we update its status only')
            }
        else:
            picking_obj = self.env['external.stock.picking'].sudo(6).create(picking_vals)
            # lines
            for line_item in message_body['line_items']:
                # vals
                line_vals = {
                    'line_id': str(line_item['id']),
                    'external_id': str(line_item['product_id']),
                    'external_variant_id': str(line_item['variation_id']),
                    'external_stock_picking_id': picking_obj.id,
                    'title': str(line_item['name']),
                    'quantity': int(line_item['quantity'])
                }
                self.env['external.stock.picking.line'].sudo(6).create(line_vals)
            # action_run
            picking_obj.action_run()
            # delete_message
            result_message['delete_message'] = True
        # return
        return result_message

    @api.multi
    def init_api_woocommerce(self):
        for item in self:
            wcapi = API(
                url=str(item.url),
                consumer_key=str(item.api_key),
                consumer_secret=str(item.api_secret),
                wp_api=True,
                version="wc/v3",
                query_string_auth=True
            )
            return wcapi
    
    @api.multi
    def action_api_status_valid(self):
        for item in self:
            if item.type == 'woocommerce':
                result_item = False
                # operations
                if item.url and item.api_key and item.api_secret:
                    # wcapi
                    wcapi = item.init_api_woocommerce()[0]
                    # get
                    response = wcapi.get("").json()
                    if 'routes' in response:
                        result_item = True
                # return
                return result_item
            else:
                return super(ExternalSource, self).action_api_status_valid()
    
    @api.multi
    def action_operations_get_products(self):
        for item in self:
            if item.type == 'woocommerce':
                item.action_operations_get_products_woocommerce()
        # super
        return_item = super(ExternalSource, self).action_operations_get_products()
        # return
        return return_item

    @api.multi
    def action_operations_get_products_woocommerce(self):
        # wcapi
        wcapi = self.init_api_woocommerce()[0]
        _logger.info(wcapi)
        # get
        # response = wcapi.get("products").json()
        page = 1
        while True:
            url = "products?per_page=100&page=%s&status=publish" % page
            response = wcapi.get(url).json()
            if 'message' in response:
                _logger.info('Query error')
                _logger.info(response)
                break
            else:
                if len(response) == 0:  # no more products
                    break
                # operations
                for response_item in response:
                    if len(response_item['variations']) == 0:
                        items = self.env['external.product'].sudo().search(
                            [
                                ('external_source_id', '=', self.id),
                                ('external_id', '=', str(response_item['id'])),
                                ('external_variant_id', '=', False)
                            ]
                        )
                        if len(items) == 0:
                            vals = {
                                'external_source_id': self.id,
                                'external_id': str(response_item['id']),
                                'sku': str(response_item['sku']),
                                'name': response_item['name'],
                            }
                            self.env['external.product'].create(vals)
                    else:
                        for variation in response_item['variations']:
                            items = self.env['external.product'].sudo().search(
                                [
                                    ('external_source_id', '=', self.id),
                                    ('external_id', '=', str(response_item['id'])),
                                    ('external_variant_id', '=', str(variation))
                                ]
                            )
                            if len(items) == 0:
                                vals = {
                                    'external_source_id': self.id,
                                    'external_id': str(response_item['id']),
                                    'external_variant_id': str(variation),
                                    'sku': str(response_item['sku']),
                                    'name': response_item['name'],
                                }
                                self.env['external.product'].create(vals)
                # increase_page
                page = page + 1

    @api.model
    def cron_external_product_stock_sync_woocommerce(self):
        source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'woocommerce'),
                ('api_status', '=', 'valid')
            ]
        )
        if source_ids:
            for source_id in source_ids:
                product_ids = self.env['external.product'].sudo().search(
                    [
                        ('external_source_id', '=', source_id.id),
                        ('product_template_id', '!=', False),
                        ('stock_sync', '=', True)
                    ]
                )
                if product_ids:
                    # wcapi (init)
                    wcapi = source_id.init_api_woocommerce()[0]
                    # external_product_ids
                    for product_id in product_ids:
                        # stock_quant
                        qty_item = 0
                        stock_quant_ids = self.env['stock.quant'].sudo().search(
                            [
                                ('product_id', '=',
                                 product_id.product_template_id.id),
                                ('location_id.usage', '=', 'internal')
                            ]
                        )
                        if stock_quant_ids:
                            for stock_quant_id in stock_quant_ids:
                                qty_item += stock_quant_id.qty
                        # data
                        data = {
                            'stock_status': 'instock'
                        }
                        if qty_item < 0:
                            data['stock_status'] = 'outofstock'
                        # operations_update
                        if product_id.external_variant_id == False:
                            response = wcapi.put(
                                "products/%s" % product_id.external_id,
                                data
                            ).json()
                        else:
                            response = wcapi.put("products/%s/variations/%s" % (
                                product_id.external_id,
                                product_id.external_variant_id
                            ), data).json()
                        # response
                        if 'id' not in response:
                            _logger.info('Failed to update stock')
                            _logger.info(response)
