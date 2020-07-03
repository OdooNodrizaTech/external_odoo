# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import dateutil.parser
import pytz

import requests, json
import shopify
#https://github.com/Shopify/shopify_api/wiki/API-examples
#https://shopify.dev/docs/admin-api/rest/reference/orders/order

class ExternalSource(models.Model):
    _inherit = 'external.source'        
    
    authorize_url = fields.Char(
        compute='_authorize_url',        
        string='Authorize Url'
    )    
    shopify_access_token = fields.Char(        
        string='Shopify Access Token'
    ) 
    shopify_location_id = fields.Char(        
        string='Shopify Location Id',
        help='Shopify Location ID (Default)'
    )

    @api.one
    def generate_external_sale_order_shopify(self, vals):
        # result_message
        result_message = {
            'statusCode': 200,
            'return_body': 'OK',
            'delete_message': False,
            'message': vals
        }
        # external_sale_order
        external_sale_order_vals = {
            'external_id': str(vals['id']),
            'external_source_id': self.id,
            'shopify_state': str(vals['financial_status'])
        }
        # fix date
        processed_at = dateutil.parser.parse(str(vals['processed_at']))
        processed_at = processed_at.replace() - processed_at.utcoffset()
        external_sale_order_vals['date'] = processed_at.strftime("%Y-%m-%d %H:%M:%S")
        # order_fields_need_check
        order_fields_need_check = ['number', 'total_price', 'subtotal_price', 'total_tax', 'total_discounts', 'total_line_items_price', 'source_name', 'landing_site']
        for order_field_need_check in order_fields_need_check:
            if order_field_need_check in vals:
                if vals[order_field_need_check] != '':
                    external_sale_order_vals[order_field_need_check] = str(vals[order_field_need_check])
        # fix source_name
        if 'source_name' in external_sale_order_vals:
            external_sale_order_vals['shopify_source_name'] = external_sale_order_vals['source_name']
            del external_sale_order_vals['source_name']
            # Fix
            if external_sale_order_vals['shopify_source_name'] not in ['web', 'pos', 'shopify_draft_order', 'iphone', 'android']:
                external_sale_order_vals['shopify_source_name'] = 'unknown'  # Force imposible value
        # shopify_landing_site
        if 'landing_site' in external_sale_order_vals:
            external_sale_order_vals['shopify_landing_site'] = external_sale_order_vals['landing_site']
            del external_sale_order_vals['landing_site']
        # total_shipping_price_set
        if 'total_shipping_price_set' in vals:
            if 'shop_money' in vals['total_shipping_price_set']:
                if 'amount' in vals['total_shipping_price_set']['shop_money']:
                    external_sale_order_vals['total_shipping_price'] = vals['total_shipping_price_set']['shop_money']['amount']
        # currency
        res_currency_ids = self.env['res.currency'].sudo().search([('name', '=', str(vals['currency']))])
        if len(res_currency_ids) > 0:
            external_sale_order_vals['currency_id'] = res_currency_ids[0].id
        # shopify_fulfillment_id
        if 'fulfillments' in vals:
            if len(vals['fulfillments']) > 0:
                fulfillments_0 = vals['fulfillments'][0]
                external_sale_order_vals['shopify_fulfillment_id'] = str(fulfillments_0['id'])
                # shopify_fulfillment_status
        if 'fulfillment_status' in vals:
            if vals['fulfillment_status'] != None:
                if str(vals['fulfillment_status']) != '':
                    external_sale_order_vals['shopify_fulfillment_status'] = str(vals['fulfillment_status'])
        # external_customer
        external_customer_vals = {
            'external_id': str(vals['customer']['id']),
            'external_source_id': self.id,
            'accepts_marketing': vals['customer']['accepts_marketing'],
            'active': True
        }
        # vat
        if 'note' in vals:
            if vals['note'] != '':
                if vals['note'] != None:
                    external_customer_vals['vat'] = str(vals['note'])
        # cutomer_fields_need_check
        cutomer_fields_need_check = ['email', 'first_name', 'last_name', 'phone', 'zip']
        for cutomer_field_need_check in cutomer_fields_need_check:
            if cutomer_field_need_check in vals['customer']:
                if vals['customer'][cutomer_field_need_check] != '':
                    if vals['customer'][cutomer_field_need_check] != None:
                        external_customer_vals[cutomer_field_need_check] = str(vals['customer'][cutomer_field_need_check])
        # customer default_address
        if 'default_address' in vals['customer']:
            customer_default_address_fields_need_check = ['address1', 'address2', 'city', 'phone', 'company', 'country_code', 'province_code']
            for customer_default_address_field_need_check in customer_default_address_fields_need_check:
                if customer_default_address_field_need_check in vals['customer']['default_address']:
                    if vals['customer']['default_address'][customer_default_address_field_need_check] != None:
                        if str(vals['customer']['default_address'][customer_default_address_field_need_check]) != '':
                            if customer_default_address_field_need_check not in external_customer_vals:
                                external_customer_vals[customer_default_address_field_need_check] = str(vals['customer']['default_address'][customer_default_address_field_need_check])
            # customer_replace_fields
            customer_replace_fields = {
                'address1': 'address_1',
                'address2': 'address_2',
                'zip': 'postcode'
            }
            for customer_replace_field in customer_replace_fields:
                if customer_replace_field in external_customer_vals:
                    new_field = customer_replace_fields[customer_replace_field]
                    external_customer_vals[new_field] = external_customer_vals[customer_replace_field]
                    del external_customer_vals[customer_replace_field]
        # search_previous
        external_customer_ids = self.env['external.customer'].sudo().search(
            [
                ('external_source_id', '=', self.id),
                ('external_id', '=', str(vals['customer']['id']))
            ]
        )
        if len(external_customer_ids) > 0:
            external_customer_obj = external_customer_ids[0]
        else:
            # create
            external_customer_obj = self.env['external.customer'].sudo(6).create(external_customer_vals)
        # define
        external_sale_order_vals['external_customer_id'] = external_customer_obj.id
        # address_types
        address_types = ['billing_address', 'shipping_address']
        for address_type in address_types:
            if address_type in vals:
                external_address_vals = {
                    'external_id': external_sale_order_vals['external_id'],
                    'external_customer_id': external_customer_obj.id,
                    'external_source_id': self.id,
                    'type': 'invoice'
                }
                # address_fields_need_check
                address_fields_need_check = ['first_name', 'address1', 'phone', 'city', 'zip', 'last_name', 'address2', 'company', 'latitude', 'longitude', 'country_code', 'province_code']
                for address_field_need_check in address_fields_need_check:
                    if address_field_need_check in vals[address_type]:
                        if vals[address_type][address_field_need_check] != '':
                            if vals[address_type][address_field_need_check] != None:
                                external_address_vals[address_field_need_check] = str(vals[address_type][address_field_need_check])
                # replace
                if 'zip' in external_address_vals:
                    external_address_vals['postcode'] = str(external_address_vals['zip'])
                    del external_address_vals['zip']
                # type
                if address_type == 'shipping_address':
                    external_address_vals['type'] = 'delivery'
                # fix_external_address_vals
                external_address_vals['external_id'] += '_' + str(external_address_vals['type'])
                # search_previous
                external_address_ids = self.env['external.address'].sudo().search(
                    [
                        ('external_source_id', '=', self.id),
                        ('external_customer_id', '=', external_address_vals['external_customer_id']),
                        ('external_id', '=', external_address_vals['external_id']),
                        ('type', '=', external_address_vals['type'])
                    ]
                )
                if len(external_address_ids) > 0:
                    external_address_obj = external_address_ids[0]
                else:
                    # create
                    external_address_obj = self.env['external.address'].sudo(6).create(external_address_vals)
                # define address_id
                if address_type == 'billing_address':
                    external_sale_order_vals['external_billing_address_id'] = external_address_obj.id
                else:
                    external_sale_order_vals['external_shipping_address_id'] = external_address_obj.id
        # external_sale_order
        _logger.info(external_sale_order_vals)
        external_sale_order_ids = self.env['external.sale.order'].sudo().search(
            [
                ('external_source_id', '=', self.id),
                ('external_id', '=', str(external_sale_order_vals['external_id']))
            ]
        )
        if len(external_sale_order_ids) > 0:
            external_sale_order_id = external_sale_order_ids[0]
            external_sale_order_id.shopify_state = str(vals['financial_status'])
            # update_shopify_fulfillment_id
            if 'shopify_fulfillment_id' in external_sale_order_vals:
                external_sale_order_id['shopify_fulfillment_id'] = str(external_sale_order_vals['shopify_fulfillment_id'])
            # shopify_fulfillment_status
            if 'shopify_fulfillment_status' in external_sale_order_vals:
                external_sale_order_id['shopify_fulfillment_status'] = str(external_sale_order_vals['shopify_fulfillment_status'])
            # action_run (only if need)
            external_sale_order_id.action_run()
            # result_message
            result_message['delete_message'] = True
            result_message['return_body'] = {'message': 'Como ya existe, actualizamos el estado del mismo unicamente'}
        else:
            # create
            external_sale_order_obj = self.env['external.sale.order'].sudo(6).create(external_sale_order_vals)
            # discount_applications
            if 'discount_applications' in vals:
                if len(vals['discount_applications']) > 0:
                    for discount_application_item in vals['discount_applications']:
                        # vals
                        external_sale_order_discount_vals = {
                            'currency_id': external_sale_order_obj.currency_id.id,
                            'external_sale_order_id': external_sale_order_obj.id
                        }
                        # discount_line_fields_need_check
                        discount_line_fields_need_check = ['type', 'value', 'value_type', 'description', 'title']
                        for discount_line_field_need_check in discount_line_fields_need_check:
                            if discount_line_field_need_check in discount_application_item:
                                external_sale_order_discount_vals[discount_line_field_need_check] = str(
                                    discount_application_item[discount_line_field_need_check])
                        # create
                        external_sale_order_discount_obj = self.env['external.sale.order.discount'].sudo(6).create(external_sale_order_discount_vals)
            # line_items
            for line_item in vals['line_items']:
                # product_exists
                if 'product_exists' in line_item:
                    if line_item['product_exists'] == True:
                        # vals
                        external_sale_order_line_vals = {
                            'line_id': str(line_item['id']),
                            'external_id': str(line_item['product_id']),
                            'external_sale_order_id': external_sale_order_obj.id,
                            'currency_id': external_sale_order_obj.currency_id.id,
                            'title': str(line_item['title']),
                            'quantity': int(line_item['quantity'])
                        }
                        # external_variant_id
                        if 'variant_id' in line_item:
                            if line_item['variant_id'] != '':
                                external_sale_order_line_vals['external_variant_id'] = str(line_item['variant_id'])
                        # sku
                        if 'sku' in line_item:
                            external_sale_order_line_vals['sku'] = str(line_item['sku'])
                            # price
                        if 'price_set' in line_item:
                            if 'shop_money' in line_item['price_set']:
                                if 'amount' in line_item['price_set']['shop_money']:
                                    external_sale_order_line_vals['price'] = line_item['price_set']['shop_money']['amount']
                        # price
                        if 'total_discount_set' in line_item:
                            if 'shop_money' in line_item['total_discount_set']:
                                if 'amount' in line_item['total_discount_set']['shop_money']:
                                    external_sale_order_line_vals['total_discount'] = line_item['total_discount_set']['shop_money']['amount']
                        # tax_amount
                        if 'tax_lines' in line_item:
                            for tax_line in line_item['tax_lines']:
                                external_sale_order_line_vals['tax_amount'] = tax_line['price']
                        # create
                        external_sale_order_line_obj = self.env['external.sale.order.line'].sudo(6).create(external_sale_order_line_vals)
            # shipping_lines
            if 'shipping_lines' in vals:
                for shipping_line in vals['shipping_lines']:
                    # vals
                    external_sale_order_shipping_vals = {
                        'external_id': str(shipping_line['id']),
                        'currency_id': external_sale_order_obj.currency_id.id,
                        'external_sale_order_id': external_sale_order_obj.id
                    }
                    # shipping_line_fields_need_check
                    shipping_line_fields_need_check = ['title', 'price', 'discounted_price']
                    for shipping_line_field_need_check in shipping_line_fields_need_check:
                        if shipping_line_field_need_check in shipping_line:
                            external_sale_order_shipping_vals[shipping_line_field_need_check] = str(shipping_line[shipping_line_field_need_check])
                    # tax_amount
                    if 'tax_lines' in shipping_line:
                        for tax_line in shipping_line['tax_lines']:
                            external_sale_order_shipping_vals['tax_amount'] = tax_line['price']
                    # create
                    external_sale_order_shipping_obj = self.env['external.sale.order.shipping'].sudo(6).create(external_sale_order_shipping_vals)
            # action_run
            external_sale_order_obj.action_run()
            # delete_message
            result_message['delete_message'] = True
        #return
        return result_message
    
    @api.one        
    def _authorize_url(self):                      
        if self.api_key!=False and self.url!=False and self.type=='shopify':
            session = shopify.Session(self.url, '2020-01')
            session.api_key = self.api_key
            scope = ['write_orders', 'read_products', 'write_inventory']
            url_redirect = str(self.env['ir.config_parameter'].sudo().get_param('web.base.url'))+'/shopify_permission'
            self.authorize_url = session.create_permission_url(scope, url_redirect)        
    
    @api.one
    def shopify_request_token(self, params):
        if self.api_status=='draft':
            #request mode (work)
            url = 'https://'+str(self.url)+'/admin/oauth/access_token'
            payload = {
                'client_id': str(self.api_key),
                'client_secret': str(self.api_secret),
                'code': str(params['code']),
            }
            headers = {
                'Content-Type': 'application/json'
            }                         
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code!=200:
                _logger.info(response.text)
            else:
                response_json = json.loads(response.text)
                if 'access_token' in response_json:
                    self.shopify_access_token = str(response_json['access_token'])
                    #session
                    session = shopify.Session(self.url, '2020-01', self.shopify_access_token)
                    shopify.ShopifyResource.activate_session(session)
                    #api_status
                    self.api_status = 'valid'     
                    
    @api.one
    def init_api_shopify(self):
        #session
        session = shopify.Session(self.url, '2020-01', self.shopify_access_token)
        shopify.ShopifyResource.activate_session(session)
        #return
        return session
        
    @api.one
    def action_operations_get_products(self):
        #operations
        if self.type=='shopify':
            self.action_operations_get_products_shopify()
        #super            
        return_item = super(ExternalSource, self).action_operations_get_products()
        # return
        return return_item
            
    @api.one
    def action_operations_get_products_shopify(self):
        #init
        self.init_api_shopify()                
        #products
        products = shopify.Product.find(limit=100)
        for product in products:
            for variant in product.variants:
                #search
                external_product_ids = self.env['external.product'].sudo().search(
                    [
                        ('external_source_id', '=', self.id),
                        ('external_id', '=', str(product.id)),
                        ('external_variant_id', '=', str(variant.id))
                    ]                    
                )
                if len(external_product_ids)==0:  
                    external_product_vals = {
                        'external_source_id': self.id,
                        'external_id': str(product.id),
                        'external_variant_id': str(variant.id),
                        'sku': str(variant.sku),
                        'name': str(product.title)+' '+str(variant.title),
                    }
                    external_product_obj = self.env['external.product'].create(external_product_vals)
        #return
        return False        
    
    @api.one
    def action_api_status_draft(self):
        return_item = super(ExternalSource, self).action_api_status_draft()
        #extra
        self.shopify_access_token = False
        #return
        return return_item
    
    @api.one
    def action_api_status_valid(self):
        #result_item        
        if self.type=='shopify':
            result_item = False
            #operations
            if self.shopify_code==False:
                raise Warning("Falta el shopify_code")
            else:
                raise Warning("Se validara a traves del link de autorizacion")                                
            #return        
            return result_item
        else:
            return super(ExternalSource, self).action_api_status_valid()

    @api.multi
    def cron_external_product_stock_sync_shopify(self, cr=None, uid=False, context=None):
        _logger.info('cron_external_product_stock_sync')
        external_source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'shopify'),
                ('api_status', '=', 'valid'),
                ('shopify_location_id', '!=', False)
            ]
        )
        if len(external_source_ids) > 0:
            for external_source_id in external_source_ids:
                external_product_ids = self.env['external.product'].sudo().search(
                    [
                        ('external_source_id', '=', external_source_id.id),
                        ('product_template_id', '!=', False),
                        ('stock_sync', '=', True)
                    ]
                )
                if len(external_product_ids) > 0:
                    # shopify (init)
                    external_source_id.init_api_shopify()[0]
                    #external_product_ids
                    for external_product_id in external_product_ids:
                        #stock_quant
                        qty_item = 0
                        stock_quant_ids = self.env['stock.quant'].sudo().search(
                            [
                                ('product_id', '=', external_product_id.product_template_id.id),
                                ('location_id.usage', '=', 'internal')
                            ]
                        )
                        if len(stock_quant_ids) > 0:
                            for stock_quant_id in stock_quant_ids:
                                qty_item += stock_quant_id.qty
                        #qty_item
                        product = shopify.Product.find(external_product_id.external_id)
                        for variant in product.variants:
                            if str(variant.id)==str(external_product_id.external_variant_id):
                                inventory_level = shopify.InventoryLevel.set(
                                    location_id=external_source_id.shopify_location_id,
                                    inventory_item_id=variant.inventory_item_id,
                                    available=int(qty_item),
                                    disconnect_if_necessary=False
                                )