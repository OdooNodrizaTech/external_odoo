# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import dateutil.parser
import pytz

from woocommerce import API

class ExternalSource(models.Model):
    _inherit = 'external.source'

    @api.one
    def generate_external_sale_order_woocommerce(self, vals):
        #result_message
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
            'woocommerce_state': str(vals['status']),
            'number': str(vals['number']),
            'total_price': str(vals['total']),
            'total_tax': str(vals['total_tax']),
            'total_discounts': str(vals['discount_total'])
        }
        # Fix date
        date_created = dateutil.parser.parse(str(vals['date_created']))
        external_sale_order_vals['date'] = date_created.strftime("%Y-%m-%d %H:%M:%S")
        # currency
        res_currency_ids = self.env['res.currency'].sudo().search([('name', '=', str(vals['currency']))])
        if len(res_currency_ids) > 0:
            res_currency_id = res_currency_ids[0]
            external_sale_order_vals['currency_id'] = res_currency_id.id
        # external_customer
        external_customer_vals = {
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
                    external_customer_vals['vat'] = str(meta_data_item['value'])
                    # fields_billing
        fields_billing = ['email', 'phone']
        for field_billing in fields_billing:
            if field_billing in vals['billing']:
                if vals['billing'][field_billing] != '':
                    external_customer_vals[field_billing] = str(vals['billing'][field_billing])
                    # fields_shipping
        fields_shipping = ['first_name', 'last_name', 'company', 'address_1', 'address_2', 'city', 'postcode']
        for field_shipping in fields_shipping:
            if field_shipping in vals['shipping']:
                if vals['shipping'][field_shipping] != '':
                    external_customer_vals[field_shipping] = str(vals['shipping'][field_shipping])
        # fix external_id=0
        if external_customer_vals['external_id'] == 0:
            if 'email' in external_customer_vals:
                external_customer_vals['external_id'] = str(external_customer_vals['email'])
        # search_previous
        external_customer_ids = self.env['external.customer'].sudo().search(
            [
                ('external_source_id', '=', self.id),
                ('external_id', '=', str(vals['customer_id']))
            ]
        )
        if len(external_customer_ids) > 0:
            external_customer_obj = external_customer_ids[0]
        else:
            # create
            external_customer_obj = self.env['external.customer'].sudo(6).create(external_customer_vals)
        # define
        external_sale_order_vals['external_customer_id'] = external_customer_obj.id
        # external_address
        address_types = ['billing', 'shipping']
        for address_type in address_types:
            # vals
            external_address_vals = {
                'external_id': external_sale_order_vals['external_id'],
                'external_customer_id': external_customer_obj.id,
                'external_source_id': self.id,
                'type': 'invoice'
            }
            # address_fields_need_check
            address_fields_need_check = ['first_name', 'last_name', 'company', 'address_1', 'address_2', 'city', 'state', 'postcode', 'country', 'phone']
            for address_field_need_check in address_fields_need_check:
                if address_field_need_check in vals[address_type]:
                    if vals[address_type][address_field_need_check] != '':
                        if vals[address_type][address_field_need_check] != None:
                            external_address_vals[address_field_need_check] = str(vals[address_type][address_field_need_check])
            # replace address_1
            if 'address_1' in external_address_vals:
                external_address_vals['address1'] = external_address_vals['address_1']
                del external_address_vals['address_1']
            # replace address_2
            if 'address_2' in external_address_vals:
                external_address_vals['address2'] = external_address_vals['address_2']
                del external_address_vals['address_2']
            # replace state
            if 'state' in external_address_vals:
                external_address_vals['province_code'] = external_address_vals['state']
                del external_address_vals['state']
            # replace country
            if 'country' in external_address_vals:
                external_address_vals['country_code'] = external_address_vals['country']
                del external_address_vals['country']
                # type
            if address_type == 'shipping':
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
            if address_type == 'billing':
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
            external_sale_order_id.woocommerce_state = str(vals['status'])
            # action_run (only if need)
            external_sale_order_id.action_run()
            # result_message
            result_message['delete_message'] = True
            result_message['return_body'] = {'message': 'Como ya existe, actualizamos el estado del mismo unicamente'}
        else:
            # create
            external_sale_order_obj = self.env['external.sale.order'].sudo(6).create(external_sale_order_vals)
            # update subtotal_price
            external_sale_order_obj.subtotal_price = external_sale_order_obj.total_price - external_sale_order_obj.total_tax
            # line_items
            for line_item in vals['line_items']:
                # vals
                external_stock_picking_line_vals = {
                    'line_id': str(line_item['id']),
                    'external_id': str(line_item['product_id']),
                    'external_sale_order_id': external_sale_order_obj.id,
                    'currency_id': external_sale_order_obj.currency_id.id,
                    'sku': str(line_item['sku']),
                    'title': str(line_item['name']),
                    'quantity': int(line_item['quantity']),
                    'price': line_item['price'],
                    'tax_amount': line_item['total_tax']
                }
                # variation_id
                if 'variation_id' in line_item:
                    if line_item['variation_id'] != '':
                        external_stock_picking_line_vals['external_variant_id'] = str(line_item['variation_id'])
                # create
                external_stock_picking_line_obj = self.env['external.sale.order.line'].sudo(6).create(external_stock_picking_line_vals)
            # shipping_lines
            for shipping_line in vals['shipping_lines']:
                # vals
                external_sale_order_shipping_vals = {
                    'external_id': str(shipping_line['id']),
                    'currency_id': external_sale_order_obj.currency_id.id,
                    'external_sale_order_id': external_sale_order_obj.id,
                    'title': str(shipping_line['method_title']),
                    'price': shipping_line['total'],
                    'tax_amount': shipping_line['total_tax']
                }
                # create
                external_sale_order_shipping_obj = self.env['external.sale.order.shipping'].sudo(6).create(external_sale_order_shipping_vals)
            # action_run
            external_sale_order_obj.action_run()
            # delete_message
            result_message['delete_message'] = True
        #return
        return result_message

    @api.one
    def generate_external_stock_picking_woocommerce(self, vals):
        #result_message
        result_message = {
            'statusCode': 200,
            'return_body': 'OK',
            'delete_message': False,
            'message': vals
        }
        # external_customer
        external_customer_vals = {
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
                    external_customer_vals['vat'] = str(meta_data_item['value'])
                    # fields_billing
        fields_billing = ['email', 'phone']
        for field_billing in fields_billing:
            if field_billing in vals['billing']:
                if vals['billing'][field_billing] != '':
                    external_customer_vals[field_billing] = str(vals['billing'][field_billing])
                    # fields_shipping
        fields_shipping = ['first_name', 'last_name', 'company', 'address_1', 'address_2', 'city', 'postcode']
        for field_shipping in fields_shipping:
            if field_shipping in vals['shipping']:
                if vals['shipping'][field_shipping] != '':
                    external_customer_vals[field_shipping] = str(vals['shipping'][field_shipping])
        # fix external_id=0
        if external_customer_vals['external_id'] == 0:
            if 'email' in external_customer_vals:
                external_customer_vals['external_id'] = str(external_customer_vals['email'])
        # search_previous
        external_customer_ids = self.env['external.customer'].sudo().search(
            [
                ('external_source_id', '=', self.id),
                ('external_id', '=', str(external_customer_vals['external_id']))
            ]
        )
        if len(external_customer_ids) > 0:
            external_customer_obj = external_customer_ids[0]
        else:
            # create
            external_customer_obj = self.env['external.customer'].sudo(6).create(external_customer_vals)
        # external_stock_picking
        external_stock_picking_vals = {
            'external_id': str(vals['id']),
            'external_customer_id': external_customer_obj.id,
            'external_source_id': self.id,
            'woocommerce_state': str(vals['status']),
            'number': str(vals['number']),
            'external_source_name': 'web'
        }
        # search_previous
        external_stock_picking_ids = self.env['external.stock.picking'].sudo().search(
            [
                ('external_id', '=', str(external_stock_picking_vals['external_id'])),
                ('external_source_id', '=', self.id)
            ]
        )
        if len(external_stock_picking_ids) > 0:
            external_stock_picking_id = external_stock_picking_ids[0]
            external_stock_picking_id.woocommerce_state = str(vals['status'])
            # action_run (only if need)
            external_stock_picking_id.action_run()
            # result_message
            result_message['delete_message'] = True
            result_message['return_body'] = {'message': 'Como ya existe, actualizamos el estado del mismo unicamente'}
        else:
            external_stock_picking_obj = self.env['external.stock.picking'].sudo(6).create(external_stock_picking_vals)
            # lines
            for line_item in message_body['line_items']:
                # vals
                external_stock_picking_line_vals = {
                    'line_id': str(line_item['id']),
                    'external_id': str(line_item['product_id']),
                    'external_variant_id': str(line_item['variation_id']),
                    'external_stock_picking_id': external_stock_picking_obj.id,
                    'title': str(line_item['name']),
                    'quantity': int(line_item['quantity'])
                }
                external_stock_picking_line_obj = self.env['external.stock.picking.line'].sudo(6).create(external_stock_picking_line_vals)
            # action_run
            external_stock_picking_obj.action_run()
            # delete_message
            result_message['delete_message'] = True
        #return
        return result_message

    @api.one
    def init_api_woocommerce(self):
        wcapi = API(
            url=str(self.url),
            consumer_key=str(self.api_key),
            consumer_secret=str(self.api_secret),
            wp_api=True,
            version="wc/v3",
            query_string_auth=True
        )
        return wcapi
    
    @api.one
    def action_api_status_valid(self):
        #result_item        
        if self.type=='woocommerce':
            result_item = False
            #operations
            if self.url!=False and self.api_key!=False and self.api_secret!=False:
                #wcapi
                wcapi = self.init_api_woocommerce()[0]                
                #get
                response = wcapi.get("").json()
                if 'routes' in response:
                    result_item = True
            #return        
            return result_item
        else:
            return super(ExternalSource, self).action_api_status_valid()            
    
    @api.one
    def action_operations_get_products(self):
        #operations
        if self.type=='woocommerce':
            self.action_operations_get_products_woocommerce()
        #super            
        return_item = super(ExternalSource, self).action_operations_get_products()
        # return
        return return_item
            
    @api.one
    def action_operations_get_products_woocommerce(self):
        _logger.info('action_operations_get_products_woocommerce')        
        #wcapi
        wcapi = self.init_api_woocommerce()[0]
        _logger.info(wcapi)        
        #get
        #response = wcapi.get("products").json()
        page = 1
        while True:
            response = wcapi.get("products?per_page=100&page="+str(page)+"&status=publish").json()
            if 'message' in response:
                _logger.info('Error en la consulta')
                _logger.info(response)
                break
            else:
                if len(response) == 0:  # no more products
                    break
                #operations
                for response_item in response:
                    if len(response_item['variations'])==0:
                        external_product_ids = self.env['external.product'].sudo().search(
                            [
                                ('external_source_id', '=', self.id),
                                ('external_id', '=', str(response_item['id'])),
                                ('external_variant_id', '=', False)
                            ]
                        )
                        if len(external_product_ids)==0:
                            external_product_vals = {
                                'external_source_id': self.id,
                                'external_id': str(response_item['id']),
                                'sku': str(response_item['sku']),
                                'name': response_item['name'],
                            }
                            external_product_obj = self.env['external.product'].create(external_product_vals)
                    else:
                        for variation in response_item['variations']:
                            external_product_ids = self.env['external.product'].sudo().search(
                                [
                                    ('external_source_id', '=', self.id),
                                    ('external_id', '=', str(response_item['id'])),
                                    ('external_variant_id', '=', str(variation))
                                ]
                            )
                            if len(external_product_ids)==0:
                                external_product_vals = {
                                    'external_source_id': self.id,
                                    'external_id': str(response_item['id']),
                                    'sku': str(response_item['sku']),
                                    'external_variant_id': str(variation),
                                    'name': response_item['name'],
                                }
                                external_product_obj = self.env['external.product'].create(external_product_vals)
                #increase_page
                page = page + 1

    @api.multi
    def cron_external_product_stock_sync_woocommerce(self, cr=None, uid=False, context=None):
        _logger.info('cron_external_product_stock_sync_woocommerce')
        external_source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'woocommerce'),
                ('api_status', '=', 'valid')
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
                    # wcapi (init)
                    wcapi = external_source_id.init_api_woocommerce()[0]
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
                        #data
                        data = {
                            'stock_status': 'instock'
                        }
                        if qty_item<0:
                            data['stock_status'] = 'outofstock'
                        #operations_update
                        if external_product_id.external_variant_id==False:
                            response = wcapi.put("products/"+str(external_product_id.external_id), data).json()
                        else:
                            response = wcapi.put("products/"+str(external_product_id.external_id)+"/variations/"+str(external_product_id.external_variant_id), data).json()
                        #response
                        if 'id' not in response:
                            _logger.info('Error al actualizar el stock')
                            _logger.info(response)