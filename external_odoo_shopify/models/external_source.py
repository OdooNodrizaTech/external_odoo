# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# https://github.com/Shopify/shopify_api/wiki/API-examples
# https://shopify.dev/docs/admin-api/rest/reference/orders/order
import logging
from odoo import api, fields, models, _
from odoo.exceptions import Warning as UserError
import dateutil.parser
import requests
import json
import shopify
_logger = logging.getLogger(__name__)


class ExternalSource(models.Model):
    _inherit = 'external.source'

    authorize_url = fields.Char(
        compute='_compute_authorize_url',
        string='Authorize Url'
    )
    shopify_access_token = fields.Char(
        string='Shopify Access Token'
    )
    shopify_location_id = fields.Char(
        string='Shopify Location Id',
        help='Shopify Location ID (Default)'
    )

    @api.multi
    def generate_external_sale_order_shopify(self, vals):
        for item in self:
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
                'external_source_id': item.id,
                'shopify_state': str(vals['financial_status'])
            }
            # fix date
            processed_at = dateutil.parser.parse(str(vals['processed_at']))
            processed_at = processed_at.replace() - processed_at.utcoffset()
            order_vals['date'] = processed_at.strftime("%Y-%m-%d %H:%M:%S")
            # order_fields_need_check
            ofnc = [
                'number', 'total_price', 'subtotal_price', 'total_tax',
                'total_discounts', 'total_line_items_price', 'source_name',
                'landing_site'
            ]
            for fnc in ofnc:
                if fnc in vals:
                    if vals[fnc] != '':
                        order_vals[fnc] = str(vals[fnc])
            # fix source_name
            if 'source_name' in order_vals:
                order_vals['shopify_source_name'] = order_vals['source_name']
                del order_vals['source_name']
                # Fix
                if order_vals['shopify_source_name'] not in \
                        ['web', 'pos', 'shopify_draft_order', 'iphone', 'android']:
                    order_vals['shopify_source_name'] = 'unknown'
            # shopify_landing_site
            if 'landing_site' in order_vals:
                order_vals['shopify_landing_site'] = order_vals['landing_site']
                del order_vals['landing_site']
            # total_shipping_price_set
            if 'total_shipping_price_set' in vals:
                if 'shop_money' in vals['total_shipping_price_set']:
                    if 'amount' in vals['total_shipping_price_set']['shop_money']:
                        order_vals['total_shipping_price'] = \
                            vals['total_shipping_price_set']['shop_money']['amount']
            # currency
            items = self.env['res.currency'].sudo().search(
                [
                    ('name', '=', str(vals['currency']))
                ]
            )
            if items:
                order_vals['currency_id'] = items[0].id
            # shopify_fulfillment_id
            if 'fulfillments' in vals:
                if len(vals['fulfillments']) > 0:
                    fulfillments_0 = vals['fulfillments'][0]
                    order_vals['shopify_fulfillment_id'] = str(fulfillments_0['id'])
                    # shopify_fulfillment_status
            if 'fulfillment_status' in vals:
                if vals['fulfillment_status'] is not None:
                    if str(vals['fulfillment_status']) != '':
                        order_vals['shopify_fulfillment_status'] = \
                            str(vals['fulfillment_status'])
            # external_customer
            customer_vals = {
                'external_id': str(vals['customer']['id']),
                'external_source_id': item.id,
                'accepts_marketing': vals['customer']['accepts_marketing'],
                'active': True
            }
            # vat
            if 'note' in vals:
                if vals['note'] != '':
                    if vals['note'] is not None:
                        customer_vals['vat'] = str(vals['note'])
            # cutomer_fields_need_check
            cfnc = ['email', 'first_name', 'last_name', 'phone', 'zip']
            for fnc in cfnc:
                if fnc in vals['customer']:
                    if vals['customer'][fnc] != '':
                        if vals['customer'][fnc] is not None:
                            customer_vals[fnc] = \
                                str(vals['customer'][fnc])
            # customer default_address
            if 'default_address' in vals['customer']:
                cda_fields_need_check = [
                    'address1', 'address2', 'city', 'phone',
                    'company', 'country_code', 'province_code'
                ]
                for fnc in cda_fields_need_check:
                    if fnc in vals['customer']['default_address']:
                        if vals['customer']['default_address'][fnc] is not None:
                            if str(vals['customer']['default_address'][fnc]) != '':
                                if fnc not in customer_vals:
                                    customer_vals[fnc] = \
                                        str(vals['customer']['default_address'][fnc])
                # customer_replace_fields
                crf = {
                    'address1': 'address_1',
                    'address2': 'address_2',
                    'zip': 'postcode'
                }
                for rf in crf:
                    if rf in customer_vals:
                        new_field = crf[rf]
                        customer_vals[new_field] = customer_vals[rf]
                        del customer_vals[rf]
            # search_previous
            items = self.env['external.customer'].sudo().search(
                [
                    ('external_source_id', '=', item.id),
                    ('external_id', '=', str(vals['customer']['id']))
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
            # address_types
            address_types = ['billing_address', 'shipping_address']
            for address_type in address_types:
                if address_type in vals:
                    address_vals = {
                        'external_id': order_vals['external_id'],
                        'external_customer_id': customer_obj.id,
                        'external_source_id': item.id,
                        'type': 'invoice'
                    }
                    # address_fields_need_check
                    afnc = [
                        'first_name', 'address1', 'phone', 'city', 'zip',
                        'last_name', 'address2', 'company', 'latitude',
                        'longitude', 'country_code', 'province_code'
                    ]
                    for fnc in afnc:
                        if fnc in vals[address_type]:
                            if vals[address_type][fnc] != '':
                                if vals[address_type][fnc] is not None:
                                    address_vals[fnc] = str(vals[address_type][fnc])
                    # replace
                    if 'zip' in address_vals:
                        address_vals['postcode'] = str(address_vals['zip'])
                        del address_vals['zip']
                    # type
                    if address_type == 'shipping_address':
                        address_vals['type'] = 'delivery'
                    # fix_external_address_vals
                    address_vals['external_id'] += '_' + str(address_vals['type'])
                    address_vals['external_id'] = '%s_%s' % (
                        address_vals['external_id'],
                        address_vals['type']
                    )
                    # search_previous
                    items = self.env['external.address'].sudo().search(
                        [
                            ('external_source_id', '=', item.id),
                            (
                                'external_customer_id',
                                '=',
                                address_vals['external_customer_id']
                            ),
                            ('external_id', '=', address_vals['external_id']),
                            ('type', '=', address_vals['type'])
                        ]
                    )
                    if items:
                        address_obj = items[0]
                    else:
                        # create
                        address_obj = self.env['external.address'].sudo(6).create(
                            address_vals
                        )
                    # define address_id
                    if address_type == 'billing_address':
                        order_vals['external_billing_address_id'] = address_obj.id
                    else:
                        order_vals['external_shipping_address_id'] = address_obj.id
            # external_sale_order
            _logger.info(order_vals)
            items = self.env['external.sale.order'].sudo().search(
                [
                    ('external_source_id', '=', item.id),
                    ('external_id', '=', str(order_vals['external_id']))
                ]
            )
            if items:
                order_id = items[0]
                order_id.shopify_state = str(vals['financial_status'])
                # update_shopify_fulfillment_id
                if 'shopify_fulfillment_id' in order_vals:
                    order_id['shopify_fulfillment_id'] = \
                        str(order_vals['shopify_fulfillment_id'])
                # shopify_fulfillment_status
                if 'shopify_fulfillment_status' in order_vals:
                    order_id['shopify_fulfillment_status'] = \
                        str(order_vals['shopify_fulfillment_status'])
                # action_run (only if need)
                order_id.action_run()
                # result_message
                result_message['delete_message'] = True
                result_message['return_body'] = {
                    'message': _('As it already exists, we update its status only')
                }
            else:
                # create
                order_obj = self.env['external.sale.order'].sudo(6).create(
                    order_vals
                )
                # discount_applications
                if 'discount_applications' in vals:
                    if len(vals['discount_applications']) > 0:
                        for dai in vals['discount_applications']:
                            # vals
                            discount_vals = {
                                'currency_id': order_obj.currency_id.id,
                                'external_sale_order_id': order_obj.id
                            }
                            # discount_line_fields_need_check
                            dlfnc = [
                                'type', 'value', 'value_type', 'description', 'title'
                            ]
                            for fnc in dlfnc:
                                if fnc in dai:
                                    discount_vals[fnc] = str(dai[fnc])
                            # create
                            self.env['external.sale.order.discount'].sudo(6).create(
                                discount_vals
                            )
                # line_items
                for line_item in vals['line_items']:
                    # product_exists
                    if 'product_exists' in line_item:
                        if line_item['product_exists']:
                            # vals
                            line_vals = {
                                'line_id': str(line_item['id']),
                                'external_id': str(line_item['product_id']),
                                'external_sale_order_id': order_obj.id,
                                'currency_id': order_obj.currency_id.id,
                                'title': str(line_item['title']),
                                'quantity': int(line_item['quantity'])
                            }
                            # external_variant_id
                            if 'variant_id' in line_item:
                                if line_item['variant_id'] != '':
                                    line_item_vi = line_item['variant_id']
                                    line_vals['external_variant_id'] = str(line_item_vi)
                            # sku
                            if 'sku' in line_item:
                                line_vals['sku'] = str(line_item['sku'])
                                # price
                            if 'price_set' in line_item:
                                line_item_ps = line_item['price_set']
                                if 'shop_money' in line_item['price_set']:
                                    line_item_ps_sm = line_item_ps['shop_money']
                                    if 'amount' in line_item['price_set']['shop_money']:
                                        line_item_ps_sm_a = line_item_ps_sm['amount']
                                        line_vals['price'] = line_item_ps_sm_a
                            # price
                            if 'total_discount_set' in line_item:
                                line_item_tds = line_item['total_discount_set']
                                if 'shop_money' in line_item_tds:
                                    line_item_tds_sm = line_item_tds['shop_money']
                                    if 'amount' in line_item_tds_sm:
                                        line_item_tds_sm_a = line_item_tds_sm['amount']
                                        line_vals['total_discount'] = line_item_tds_sm_a
                            # tax_amount
                            if 'tax_lines' in line_item:
                                for tax_line in line_item['tax_lines']:
                                    line_vals['tax_amount'] = tax_line['price']
                            # create
                            self.env['external.sale.order.line'].sudo(6).create(
                                line_vals
                            )
                # shipping_lines
                if 'shipping_lines' in vals:
                    for shipping_line in vals['shipping_lines']:
                        # vals
                        shipping_vals = {
                            'external_id': str(shipping_line['id']),
                            'currency_id': order_obj.currency_id.id,
                            'external_sale_order_id': order_obj.id
                        }
                        # shipping_line_fields_need_check
                        slfnc = ['title', 'price', 'discounted_price']
                        for fnc in slfnc:
                            if fnc in shipping_line:
                                shipping_vals[fnc] = str(shipping_line[fnc])
                        # tax_amount
                        if 'tax_lines' in shipping_line:
                            for tax_line in shipping_line['tax_lines']:
                                shipping_vals['tax_amount'] = tax_line['price']
                        # create
                        self.env['external.sale.order.shipping'].sudo(6).create(
                            shipping_vals
                        )
                # action_run
                order_obj.action_run()
                # delete_message
                result_message['delete_message'] = True
        # return
        return result_message

    @api.multi
    @api.depends('api_key', 'url')
    def _compute_authorize_url(self):
        for item in self:
            if item.api_key and item.url and item.type == 'shopify':
                session = shopify.Session(item.url, '2020-01')
                session.api_key = item.api_key
                scope = ['write_orders', 'read_products', 'write_inventory']
                url_redirect = "%s/shopify_permission" % (
                    item.env['ir.config_parameter'].sudo().get_param('web.base.url')
                )
                item.authorize_url = session.create_permission_url(scope, url_redirect)

    @api.multi
    def shopify_request_token(self, params):
        for item in self:
            if item.api_status == 'draft':
                # request mode (work)
                url = 'https://%s/admin/oauth/access_token' % item.url
                payload = {
                    'client_id': str(item.api_key),
                    'client_secret': str(item.api_secret),
                    'code': str(params['code']),
                }
                headers = {
                    'Content-Type': 'application/json'
                }
                response = requests.post(url, headers=headers, data=json.dumps(payload))
                if response.status_code != 200:
                    _logger.info(response.text)
                else:
                    response_json = json.loads(response.text)
                    if 'access_token' in response_json:
                        item.shopify_access_token = str(response_json['access_token'])
                        # session
                        session = shopify.Session(
                            item.url,
                            '2020-01',
                            item.shopify_access_token
                        )
                        shopify.ShopifyResource.activate_session(session)
                        # api_status
                        item.api_status = 'valid'

    @api.multi
    def init_api_shopify(self):
        for item in self:
            # session
            session = shopify.Session(item.url, '2020-01', item.shopify_access_token)
            shopify.ShopifyResource.activate_session(session)
        # return
        return session

    @api.multi
    def action_operations_get_products(self):
        for item in self:
            if item.type == 'shopify':
                item.action_operations_get_products_shopify()
        # super
        return_item = super(ExternalSource, self).action_operations_get_products()
        # return
        return return_item

    @api.multi
    def action_operations_get_products_shopify(self):
        for item in self:
            item.init_api_shopify()
            # products
            products = shopify.Product.find(limit=100)
            for product in products:
                for variant in product.variants:
                    # search
                    product_ids = self.env['external.product'].sudo().search(
                        [
                            ('external_source_id', '=', item.id),
                            ('external_id', '=', str(product.id)),
                            ('external_variant_id', '=', str(variant.id))
                        ]
                    )
                    if len(product_ids) == 0:
                        vals = {
                            'external_source_id': item.id,
                            'external_id': str(product.id),
                            'external_variant_id': str(variant.id),
                            'sku': str(variant.sku),
                            'name': '%s %s' % (product.title, variant.title),
                        }
                        self.env['external.product'].create(vals)
        # return
        return False

    @api.multi
    def action_api_status_draft(self):
        return_item = super(ExternalSource, self).action_api_status_draft()
        # extra
        for item in self:
            item.shopify_access_token = False
        # return
        return return_item

    @api.multi
    def action_api_status_valid(self):
        for item in self:
            if item.type == 'shopify':
                result_item = False
                # operations
                if not item.shopify_code:
                    raise UserError(_('Shopify_code is missing'))
                else:
                    raise UserError(
                        _('It will be validated through the authorization link')
                    )
                # return
                return result_item
            else:
                return super(ExternalSource, self).action_api_status_valid()

    @api.model
    def cron_external_product_stock_sync_shopify(self):
        _logger.info('cron_external_product_stock_sync')
        source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'shopify'),
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
                    # shopify (init)
                    source_id.init_api_shopify()[0]
                    # external_product_ids
                    for product_id in product_ids:
                        # stock_quant
                        qty_item = 0
                        quant_ids = self.env['stock.quant'].sudo().search(
                            [
                                (
                                    'product_id',
                                    '=',
                                    product_id.product_template_id.id
                                ),
                                ('location_id.usage', '=', 'internal')
                            ]
                        )
                        if quant_ids:
                            for quant_id in quant_ids:
                                qty_item += quant_id.qty
                        # qty_item
                        product = shopify.Product.find(product_id.external_id)
                        for variant in product.variants:
                            product_id_ev = product_id.external_variant_id
                            if str(variant.id) == str(product_id_ev):
                                shopify.InventoryLevel.set(
                                    location_id=42284515467,
                                    inventory_item_id=variant.inventory_item_id,
                                    available=int(qty_item),
                                    disconnect_if_necessary=False
                                )
