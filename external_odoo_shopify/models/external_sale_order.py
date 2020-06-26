# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import json
import dateutil.parser
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError
import shopify
import urllib.parse as urlparse
from urllib.parse import parse_qs

class ExternalSaleOrder(models.Model):
    _inherit = 'external.sale.order'             
    
    shopify_source_name = fields.Selection(
        [
            ('unknown', 'Unknown'),
            ('web', 'Web'),
            ('pos', 'Pos'),            
            ('shopify_draft_order', 'Shopify Draft Order'),
            ('iphone', 'Iphone'),
            ('android', 'Android'),
        ],
        string='Shopify Source Name',
        default='unknown'
    )
    shopify_cancelled_at = fields.Datetime(
        string='Shopify Cancelled At'
    )
    shopify_fulfillment_id = fields.Char(
        string='Shopify Fulfillment Id'
    )
    shopify_fulfillment_status = fields.Selection(
        [
            ('none', 'None'),
            ('fulfilled', 'Fulfilled'),            
            ('null', 'Null'),
            ('partial', 'Partial'),
            ('restocked', 'Restocked'),
        ],
        string='Shopify Fulfillment Status',
        default='none'
    )
    shopify_landing_site = fields.Char(
        string='Shopify Landing Site'
    )

    @api.one
    def write(self, vals):
        return_object = super(ExternalSaleOrder, self).write(vals)
        # Fix
        if 'shopify_landing_site' in vals:
            if self.shopify_landing_site != False:
                # get params
                params = {}
                parsed = urlparse.urlparse(self.shopify_landing_site)
                params_urlparse = parse_qs(parsed.query)
                if len(params_urlparse) > 0:
                    for param_urlparse in params_urlparse:
                        params[str(param_urlparse)] = str(params_urlparse[param_urlparse][0])
                # landing_url
                self.landing_url = parsed.path
                # utm_campaign
                if 'utm_campaign' in params:
                    self.landing_utm_campaign = params['utm_campaign']
                # utm_medium
                if 'utm_medium' in params:
                    self.landing_utm_medium = params['utm_medium']
                # utm_source
                if 'utm_source' in params:
                    self.landing_utm_source = params['utm_source']
        # return
        return return_object
    
    @api.one
    def action_run(self):
        return_item = super(ExternalSaleOrder, self).action_run()
        return return_item
        
    @api.one
    def action_run(self):
        return_item = super(ExternalSaleOrder, self).action_run()
        return return_item        
    
    @api.model
    def cron_external_sale_order_update_shipping_expedition_shopify(self):
        _logger.info('cron_external_sale_order_update_shipping_expedition_shopify')
        #search
        external_source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'shopify'),
                ('api_status', '=', 'valid'),
                ('shopify_location_id', '!=', False)
            ]
        )
        if len(external_source_ids)>0:
            for external_source_id in external_source_ids:
                #external_sale_order_ids
                external_sale_order_ids = self.env['external.sale.order'].sudo().search(
                    [   
                        ('external_source_id', '=', external_source_id.id),
                        ('shopify_state', '=', 'paid'),
                        ('shopify_cancelled_at', '=', False),
                        ('sale_order_id', '!=', False),                                                                        
                        ('sale_order_id.state', 'in', ('sale', 'done')),
                        ('shopify_fulfillment_status', '=', 'none')
                    ]
                )
                if len(external_sale_order_ids)>0:
                    # shopify (init)
                    external_source_id.init_api_shopify()[0]
                    #external_sale_order_ids
                    for external_sale_order_id in external_sale_order_ids:
                        #stock_picking
                        stock_picking_ids = self.env['stock.picking'].sudo().search(
                            [   
                                ('origin', '=', str(external_sale_order_id.sale_order_id.name)),
                                ('state', '=', 'done'),
                                ('picking_type_id.code', '=', 'outgoing')
                            ]
                        )
                        if len(stock_picking_ids)>0:
                            order_id = str(external_sale_order_id.external_id)
                            location_id = str(external_source_id.shopify_location_id)
                            #order (line_items)
                            order = shopify.Order.find(order_id)
                            #cancelled_at
                            if order.cancelled_at!=None:
                                external_sale_order_id.shopify_cancelled_at = str(order.cancelled_at.replace('T', ' '))
                            #Fix continue
                            if external_sale_order_id.shopify_cancelled_at==False:                            
                                #fullfiment
                                if order.fulfillment_status!=None:                                    
                                    #fulfillments
                                    fulfillments = shopify.Fulfillment.find(order_id=order_id, limit=100)
                                    if len(fulfillments)>0:
                                        fullfiment_0 = fulfillments[0]
                                        external_sale_order_id.shopify_fulfillment_id = fullfiment_0.id
                                        external_sale_order_id.shopify_fulfillment_status = str(order.fulfillment_status)                                        
                                #check need create
                                if external_sale_order_id.shopify_fulfillment_status=='none':
                                    #line_items
                                    line_items = []
                                    for line_item in order.line_items:
                                        line_items.append({
                                            'id': line_item.id
                                        })
                                    #Fulfillment create
                                    new_fulfillment = shopify.Fulfillment(prefix_options = {'order_id': order_id})
                                    new_fulfillment.location_id = location_id
                                    new_fulfillment.line_items = line_items
                                    #new_fulfillment.notify_customer = False
                                    success = new_fulfillment.save()
                                    #update (prevent-errors)
                                    if new_fulfillment.errors:
                                        _logger.info('Error al crear')
                                    else:
                                        external_sale_order_id.shopify_fulfillment_id = new_fulfillment.id                                
                                        external_sale_order_id.shopify_fulfillment_status = 'fulfilled'#Ever fullfiled
    
    @api.model
    def cron_sqs_external_sale_order_shopify(self):
        _logger.info('cron_sqs_external_sale_order_shopify')

        sqs_url = tools.config.get('sqs_external_sale_order_shopify_url')
        AWS_ACCESS_KEY_ID = tools.config.get('aws_access_key_id')
        AWS_SECRET_ACCESS_KEY = tools.config.get('aws_secret_key_id')
        AWS_SMS_REGION_NAME = tools.config.get('aws_region_name')
        # boto3
        sqs = boto3.client(
            'sqs',
            region_name=AWS_SMS_REGION_NAME,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        # Receive message from SQS queue
        total_messages = 10
        while total_messages > 0:
            response = sqs.receive_message(
                QueueUrl=sqs_url,
                AttributeNames=['All'],
                MaxNumberOfMessages=10,
                MessageAttributeNames=['All']
            )
            if 'Messages' in response:
                total_messages = len(response['Messages'])
            else:
                total_messages = 0
            # continue
            if 'Messages' in response:
                for message in response['Messages']:
                    # message_body
                    message_body = json.loads(message['Body'])
                    # fix message
                    if 'Message' in message_body:
                        message_body = json.loads(message_body['Message'])
                    # result_message
                    result_message = {
                        'statusCode': 200,
                        'return_body': 'OK',
                        'delete_message': False,
                        'message': message_body
                    }
                    #default
                    source = 'shopify'
                    # fields_need_check
                    fields_need_check = ['id', 'customer', 'shipping_address', 'shipping_address', 'line_items', 'financial_status', 'X-Shopify-Shop-Domain']
                    for field_need_check in fields_need_check:
                        if field_need_check not in message_body:
                            result_message['statusCode'] = 500
                            result_message['delete_message'] = True
                            result_message['return_body'] = 'No existe el campo ' + str(field_need_check)                    
                    # operations
                    if result_message['statusCode'] == 200:
                        #source_url
                        source_url = str(message_body['X-Shopify-Shop-Domain'])
                        #external_source_id
                        external_source_ids = self.env['external.source'].sudo().search([('type', '=', str(source)),('url', '=', str(source_url))])
                        if len(external_source_ids)==0:
                            result_message['statusCode'] = 500
                            result_message['return_body'] = {'error': 'No existe external_source id con este source='+str(source)+' y url='+str(source_url)}
                        else:
                            external_source_id = external_source_ids[0]                        
                        #status
                        if message_body['financial_status']!='paid':
                            result_message['statusCode'] = 500
                            result_message['delete_message'] = True
                            result_message['return_body'] = {'error': 'El pedido no esta pagado (financial_status)'}
                        # create-write
                        if result_message['statusCode'] == 200:  # error, data not exists
                            #operaciones varias para crearlos                            
                            #external_sale_order
                            external_sale_order_vals = {
                                'external_id': str(message_body['id']),
                                'external_source_id': external_source_id.id,
                                'shopify_state': str(message_body['financial_status']),
                            }
                            #fix date
                            processed_at = dateutil.parser.parse(str(message_body['processed_at']))
                            processed_at = processed_at.replace() - processed_at.utcoffset()
                            external_sale_order_vals['date'] = processed_at.strftime("%Y-%m-%d %H:%M:%S")                            
                            #order_fields_need_check
                            order_fields_need_check = ['number', 'total_price', 'subtotal_price', 'total_tax', 'total_discounts', 'total_line_items_price', 'source_name', 'landing_site']
                            for order_field_need_check in order_fields_need_check:
                                if order_field_need_check in message_body:
                                    if message_body[order_field_need_check]!='':
                                        external_sale_order_vals[order_field_need_check] = str(message_body[order_field_need_check])
                            #fix source_name
                            if 'source_name' in external_sale_order_vals:
                                external_sale_order_vals['shopify_source_name'] = external_sale_order_vals['source_name'] 
                                del external_sale_order_vals['source_name']
                                #Fix
                                if external_sale_order_vals['shopify_source_name'] not in ['web', 'pos', 'shopify_draft_order', 'iphone', 'android']:
                                    external_sale_order_vals['shopify_source_name'] = 'unknown'#Force imposible value
                            #shopify_landing_site
                            if 'landing_site' in external_sale_order_vals:
                                external_sale_order_vals['shopify_landing_site'] = external_sale_order_vals[
                                    'landing_site']
                                del external_sale_order_vals['landing_site']
                            #total_shipping_price_set
                            if 'total_shipping_price_set' in message_body:
                                if 'shop_money' in message_body['total_shipping_price_set']:
                                    if 'amount' in message_body['total_shipping_price_set']['shop_money']:
                                        external_sale_order_vals['total_shipping_price'] = message_body['total_shipping_price_set']['shop_money']['amount']
                            #currency
                            res_currency_ids = self.env['res.currency'].sudo().search([('name', '=', str(message_body['currency']))])
                            if len(res_currency_ids)>0:
                                res_currency_id = res_currency_ids[0]
                                external_sale_order_vals['currency_id'] = res_currency_id.id
                            #shopify_fulfillment_id
                            if 'fulfillments' in message_body:
                                if len(message_body['fulfillments'])>0:
                                    fulfillments_0 = message_body['fulfillments'][0]
                                    external_sale_order_vals['shopify_fulfillment_id'] = str(fulfillments_0['id'])                                     
                            #shopify_fulfillment_status
                            if 'fulfillment_status' in message_body:
                                if message_body['fulfillment_status']!=None:
                                    if str(message_body['fulfillment_status'])!='':                                    
                                        external_sale_order_vals['shopify_fulfillment_status'] = str(message_body['fulfillment_status'])
                            #external_customer
                            external_customer_vals = {
                                'external_id': str(message_body['customer']['id']),
                                'external_source_id': external_source_id.id,
                                'accepts_marketing': message_body['customer']['accepts_marketing'],
                                'active': True    
                            }
                            #vat
                            if 'note' in message_body:
                                if message_body['note']!='':
                                    if message_body['note']!=None:
                                        external_customer_vals['vat'] = str(message_body['note']) 
                            #cutomer_fields_need_check
                            cutomer_fields_need_check = ['email', 'first_name', 'last_name', 'phone', 'zip']
                            for cutomer_field_need_check in cutomer_fields_need_check:
                                if cutomer_field_need_check in message_body['customer']:
                                    if message_body['customer'][cutomer_field_need_check]!='':
                                        if message_body['customer'][cutomer_field_need_check]!=None:
                                            external_customer_vals[cutomer_field_need_check] = str(message_body['customer'][cutomer_field_need_check])
                            #customer default_address
                            if 'default_address' in message_body['customer']:
                                customer_default_address_fields_need_check = ['address1', 'address2', 'city', 'phone', 'company', 'country_code', 'province_code']
                                for customer_default_address_field_need_check in customer_default_address_fields_need_check:
                                    if customer_default_address_field_need_check in message_body['customer']['default_address']:
                                        if message_body['customer']['default_address'][customer_default_address_field_need_check]!=None:
                                            if str(message_body['customer']['default_address'][customer_default_address_field_need_check])!='':                                            
                                                if customer_default_address_field_need_check not in external_customer_vals:
                                                    external_customer_vals[customer_default_address_field_need_check] = str(message_body['customer']['default_address'][customer_default_address_field_need_check])
                                #customer_replace_fields
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
                            #search_previous
                            external_customer_ids = self.env['external.customer'].sudo().search(
                                [
                                    ('external_source_id', '=', external_source_id.id),
                                    ('external_id', '=', str(message_body['customer']['id']))                                    
                                ]
                            )
                            if len(external_customer_ids)>0:
                                external_customer_obj = external_customer_ids[0]
                            else:
                                #create
                                external_customer_obj = self.env['external.customer'].sudo(6).create(external_customer_vals)
                            #define
                            external_sale_order_vals['external_customer_id'] = external_customer_obj.id
                            #address_types
                            address_types = ['billing_address', 'shipping_address']
                            for address_type in address_types:
                                if address_type in message_body:                                                                 
                                    external_address_vals = {
                                        'external_id': external_sale_order_vals['external_id'],
                                        'external_customer_id': external_customer_obj.id,
                                        'external_source_id': external_source_id.id,
                                        'type': 'invoice'                                
                                    }
                                    #address_fields_need_check
                                    address_fields_need_check = ['first_name', 'address1', 'phone', 'city', 'zip', 'last_name', 'address2', 'company', 'latitude', 'longitude', 'country_code', 'province_code']
                                    for address_field_need_check in address_fields_need_check:
                                        if address_field_need_check in message_body[address_type]:
                                            if message_body[address_type][address_field_need_check]!='':
                                                if message_body[address_type][address_field_need_check]!=None:
                                                    external_address_vals[address_field_need_check] = str(message_body[address_type][address_field_need_check])
                                    #replace
                                    if 'zip' in external_address_vals:
                                        external_address_vals['postcode'] = str(external_address_vals['zip'])
                                        del external_address_vals['zip']
                                    #type
                                    if address_type=='shipping_address':
                                        external_address_vals['type'] = 'delivery'
                                    #fix_external_address_vals
                                    external_address_vals['external_id'] += '_'+str(external_address_vals['type'])
                                    #search_previous
                                    external_address_ids = self.env['external.address'].sudo().search(
                                        [
                                            ('external_source_id', '=', external_source_id.id),
                                            ('external_customer_id', '=', external_address_vals['external_customer_id']),
                                            ('external_id', '=', external_address_vals['external_id']),
                                            ('type', '=', external_address_vals['type'])                                    
                                        ]
                                    )
                                    if len(external_address_ids)>0:
                                        external_address_obj = external_address_ids[0]
                                    else:
                                        #create
                                        external_address_obj = self.env['external.address'].sudo(6).create(external_address_vals)
                                    #define address_id
                                    if address_type=='billing_address':
                                        external_sale_order_vals['external_billing_address_id'] = external_address_obj.id
                                    else:
                                        external_sale_order_vals['external_shipping_address_id'] = external_address_obj.id
                            #external_sale_order
                            _logger.info(external_sale_order_vals)
                            external_sale_order_ids = self.env['external.sale.order'].sudo().search(
                                [
                                    ('external_source_id', '=', external_source_id.id),
                                    ('external_id', '=', str(external_sale_order_vals['external_id']))                                    
                                ]
                            )
                            if len(external_sale_order_ids)>0:
                                external_sale_order_id = external_sale_order_ids[0]
                                external_sale_order_id.shopify_state = str(message_body['financial_status'])
                                #update_shopify_fulfillment_id
                                if 'shopify_fulfillment_id' in external_sale_order_vals:
                                    external_sale_order_id['shopify_fulfillment_id'] = str(external_sale_order_vals['shopify_fulfillment_id'])
                                #shopify_fulfillment_status
                                if 'shopify_fulfillment_status' in external_sale_order_vals:
                                    external_sale_order_id['shopify_fulfillment_status'] = str(external_sale_order_vals['shopify_fulfillment_status'])
                                #action_run (only if need)
                                external_sale_order_id.action_run()
                                #result_message
                                result_message['delete_message'] = True
                                result_message['return_body'] = {'message': 'Como ya existe, actualizamos el estado del mismo unicamente'}
                            else:
                                #create
                                external_sale_order_obj = self.env['external.sale.order'].sudo(6).create(external_sale_order_vals)
                                #discount_applications
                                if 'discount_applications' in message_body:
                                    if len(message_body['discount_applications'])>0:
                                        for discount_application_item in message_body['discount_applications']:
                                            #vals
                                            external_sale_order_discount_vals = {
                                                'currency_id': external_sale_order_obj.currency_id.id,
                                                'external_sale_order_id': external_sale_order_obj.id                                                
                                            }
                                            #discount_line_fields_need_check
                                            discount_line_fields_need_check = ['type', 'value', 'value_type', 'description', 'title']
                                            for discount_line_field_need_check in discount_line_fields_need_check:
                                                if discount_line_field_need_check in discount_application_item:
                                                    external_sale_order_discount_vals[discount_line_field_need_check] = str(discount_application_item[discount_line_field_need_check])
                                            #create
                                            external_sale_order_discount_obj = self.env['external.sale.order.discount'].sudo(6).create(external_sale_order_discount_vals)
                                #line_items
                                for line_item in message_body['line_items']:
                                    #product_exists
                                    if 'product_exists' in line_item:
                                        if line_item['product_exists']==True:
                                            #vals
                                            external_sale_order_line_vals = {
                                                'line_id': str(line_item['id']),
                                                'external_id': str(line_item['product_id']),
                                                'external_sale_order_id': external_sale_order_obj.id,
                                                'currency_id': external_sale_order_obj.currency_id.id,
                                                'title': str(line_item['title']),
                                                'quantity': int(line_item['quantity'])
                                            }
                                            #external_variant_id
                                            if 'variant_id' in line_item:
                                                if line_item['variant_id']!='':
                                                    external_sale_order_line_vals['external_variant_id'] = str(line_item['variant_id'])
                                            #sku
                                            if 'sku' in line_item:
                                                external_sale_order_line_vals['sku'] = str(line_item['sku']) 
                                            #price
                                            if 'price_set' in line_item:
                                                if 'shop_money' in line_item['price_set']:
                                                    if 'amount' in line_item['price_set']['shop_money']:
                                                        external_sale_order_line_vals['price'] = line_item['price_set']['shop_money']['amount']
                                            #price
                                            if 'total_discount_set' in line_item:
                                                if 'shop_money' in line_item['total_discount_set']:
                                                    if 'amount' in line_item['total_discount_set']['shop_money']:
                                                        external_sale_order_line_vals['total_discount'] = line_item['total_discount_set']['shop_money']['amount']
                                            #tax_amount
                                            if 'tax_lines' in line_item:
                                                for tax_line in line_item['tax_lines']:
                                                    external_sale_order_line_vals['tax_amount'] = tax_line['price']                                                                                                                                                                                                          
                                            #create
                                            external_sale_order_line_obj = self.env['external.sale.order.line'].sudo(6).create(external_sale_order_line_vals)
                                #shipping_lines
                                if 'shipping_lines' in message_body: 
                                    for shipping_line in message_body['shipping_lines']:                                        
                                        #vals                                        
                                        external_sale_order_shipping_vals = {
                                            'external_id': str(shipping_line['id']),
                                            'currency_id': external_sale_order_obj.currency_id.id,
                                            'external_sale_order_id': external_sale_order_obj.id
                                        }
                                        #shipping_line_fields_need_check
                                        shipping_line_fields_need_check = ['title', 'price', 'discounted_price']
                                        for shipping_line_field_need_check in shipping_line_fields_need_check:
                                            if shipping_line_field_need_check in shipping_line:
                                                external_sale_order_shipping_vals[shipping_line_field_need_check] = str(shipping_line[shipping_line_field_need_check])
                                        #tax_amount
                                        if 'tax_lines' in shipping_line:
                                            for tax_line in shipping_line['tax_lines']:
                                                external_sale_order_shipping_vals['tax_amount'] = tax_line['price']                                                
                                        #create
                                        external_sale_order_shipping_obj = self.env['external.sale.order.shipping'].sudo(6).create(external_sale_order_shipping_vals)                                                
                                #action_run
                                external_sale_order_obj.action_run()
                                #delete_message
                                result_message['delete_message'] = True                            
                    #logger
                    _logger.info(result_message)                                                            
                    # remove_message
                    if result_message['delete_message']==True:
                        response_delete_message = sqs.delete_message(
                            QueueUrl=sqs_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )