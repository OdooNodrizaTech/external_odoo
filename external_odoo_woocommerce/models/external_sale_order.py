# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import dateutil.parser

import boto3
from botocore.exceptions import ClientError

class ExternalSaleOrder(models.Model):
    _inherit = 'external.sale.order'             
        
    @api.one
    def action_run(self):
        return_item = super(ExternalSaleOrder, self).action_run()
        return return_item        
        
    @api.multi
    def cron_external_sale_order_update_shipping_expedition_woocommerce(self, cr=None, uid=False, context=None):
        _logger.info('cron_external_sale_order_update_shipping_expedition_woocommerce')
        #search
        external_source_ids = self.env['external.source'].sudo().search([('type', '=', 'woocommerce'),('api_status', '=', 'valid')])
        if len(external_source_ids)>0:
            for external_source_id in external_source_ids:
                #external_sale_order_ids
                external_sale_order_ids = self.env['external.sale.order'].sudo().search(
                    [   
                        ('external_source_id', '=', external_source_id.id),
                        ('woocommerce_state', 'in', ('processing', 'shipped')),
                        ('sale_order_id', '!=', False),
                        ('sale_order_id.state', 'in', ('sale', 'done'))
                    ]
                )
                if len(external_sale_order_ids)>0:
                    # wcapi (init)
                    wcapi = external_source_id.init_api_woocommerce()[0]
                    #external_sale_order_ids
                    for external_sale_order_id in external_sale_order_ids:
                        #stock_picking
                        stock_picking_ids = self.env['stock.picking'].sudo().search(
                            [   
                                ('origin', '=', str(external_sale_order_id.sale_order_id.name)),
                                ('state', '=', 'done'),
                                ('picking_type_id.code', '=', 'outgoing'),                                
                                ('shipping_expedition_id', '!=', False),
                                ('shipping_expedition_id.state', '=', 'delivered')
                            ]
                        )
                        if len(stock_picking_ids)>0:                            
                            #put (#OK, se actualiza)
                            data = {"status": "completed"}                
                            response = wcapi.put("orders/"+str(external_sale_order_id.number), data).json()
                            if 'id' in response:
                                #update OK
                                external_sale_order_id.woocommerce_state = 'completed'        
    
    @api.multi
    def cron_sqs_external_sale_order_woocommerce(self, cr=None, uid=False, context=None):
        _logger.info('cron_sqs_external_sale_order_woocommerce')

        sqs_url = tools.config.get('sqs_external_sale_order_woocommerce_url')
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
                    source = 'woocommerce'
                    # fields_need_check
                    fields_need_check = ['status', 'shipping', 'billing', 'X-WC-Webhook-Source']
                    for field_need_check in fields_need_check:
                        if field_need_check not in message_body:
                            result_message['statusCode'] = 500
                            result_message['delete_message'] = True
                            result_message['return_body'] = 'No existe el campo ' + str(field_need_check)
                    # operations_1
                    if result_message['statusCode'] == 200:
                        #source_url
                        source_url = str(message_body['X-WC-Webhook-Source'])
                        #external_source_id
                        external_source_ids = self.env['external.source'].sudo().search([('type', '=', str(source)),('url', '=', str(source_url))])
                        if len(external_source_ids)==0:
                            result_message['statusCode'] = 500
                            result_message['return_body'] = {'error': 'No existe external_source id con este source='+str(source)+' y url='+str(source_url)}
                        else:
                            external_source_id = external_source_ids[0]
                        #status
                        if message_body['status'] not in ['processing', 'completed', 'shipped', 'refunded']:
                            result_message['statusCode'] = 500
                            result_message['delete_message'] = True
                            result_message['return_body'] = {'error': 'El pedido no esta completado'}
                        # create-write
                        if result_message['statusCode'] == 200:  # error, data not exists
                            #external_sale_order
                            external_sale_order_vals = {
                                'external_id': str(message_body['id']),
                                'external_source_id': external_source_id.id,
                                'woocommerce_state': str(message_body['status']),
                                'number': str(message_body['number']),
                                'total_price': str(message_body['total']),                                                                
                                'total_tax': str(message_body['total_tax']),
                                'total_discounts': str(message_body['discount_total'])
                            }
                            #Fix date
                            date_created = dateutil.parser.parse(str(message_body['date_created']))
                            date_created = date_created.replace() - date_created.utcoffset()
                            external_sale_order_vals['date'] = date_created.strftime("%Y-%m-%d %H:%M:%S")                            
                            #currency
                            res_currency_ids = self.env['res.currency'].sudo().search([('name', '=', str(message_body['currency']))])
                            if len(res_currency_ids)>0:
                                res_currency_id = res_currency_ids[0]
                                external_sale_order_vals['currency_id'] = res_currency_id.id
                            #external_customer
                            external_customer_vals = {
                                'external_source_id': external_source_id.id,
                                'active': True,
                                'external_id': int(message_body['customer_id']),
                                'province_code': str(message_body['shipping']['state']),
                                'country_code': str(message_body['shipping']['country'])                                        
                            }
                            #vat colocarlo bien aqui y en la direccion de facturacion
                            if 'meta_data' in message_body:
                                for meta_data_item in message_body['meta_data']:
                                    if meta_data_item['key']=='NIF':
                                        external_customer_vals['vat'] = str(meta_data_item['value'])                                                            
                            #fields_billing
                            fields_billing = ['email', 'phone']
                            for field_billing in fields_billing:
                                if field_billing in message_body['billing']:
                                    if message_body['billing'][field_billing]!='':
                                        external_customer_vals[field_billing] = str(message_body['billing'][field_billing])                                        
                            #fields_shipping
                            fields_shipping = ['first_name', 'last_name', 'company', 'address_1', 'address_2', 'city', 'postcode']
                            for field_shipping in fields_shipping:
                                if field_shipping in message_body['shipping']:
                                    if message_body['shipping'][field_shipping]!='':
                                        external_customer_vals[field_shipping] = str(message_body['shipping'][field_shipping])
                            #fix external_id=0
                            if external_customer_vals['external_id']==0:
                                if 'email' in external_customer_vals:
                                    external_customer_vals['external_id'] = str(external_customer_vals['email'])                                                                    
                            #search_previous
                            external_customer_ids = self.env['external.customer'].sudo().search(
                                [
                                    ('external_source_id', '=', external_source_id.id),
                                    ('external_id', '=', str(message_body['customer_id']))                                    
                                ]
                            )                            
                            if len(external_customer_ids)>0:
                                external_customer_obj = external_customer_ids[0]
                            else:
                                #create
                                external_customer_obj = self.env['external.customer'].sudo(6).create(external_customer_vals)
                            #define
                            external_sale_order_vals['external_customer_id'] = external_customer_obj.id                                                                                                   
                            #external_address
                            address_types = ['billing', 'shipping']
                            for address_type in address_types:
                                #vals
                                external_address_vals = {
                                    'external_id': external_sale_order_vals['external_id'],
                                    'external_customer_id': external_customer_obj.id,
                                    'external_source_id': external_source_id.id,
                                    'type': 'invoice'
                                }
                                #address_fields_need_check
                                address_fields_need_check = ['first_name', 'last_name', 'company', 'address_1', 'address_2', 'city', 'state', 'postcode', 'country', 'phone']
                                for address_field_need_check in address_fields_need_check:
                                    if address_field_need_check in message_body[address_type]:
                                        if message_body[address_type][address_field_need_check]!='':
                                            if message_body[address_type][address_field_need_check]!=None:
                                                external_address_vals[address_field_need_check] = str(message_body[address_type][address_field_need_check])
                                #replace address_1
                                if 'address_1' in external_address_vals:
                                    external_address_vals['address1'] = external_address_vals['address_1']
                                    del external_address_vals['address_1']
                                #replace address_2
                                if 'address_2' in external_address_vals:
                                    external_address_vals['address2'] = external_address_vals['address_2']
                                    del external_address_vals['address_2']
                                #replace state
                                if 'state' in external_address_vals:
                                    external_address_vals['province_code'] = external_address_vals['state']
                                    del external_address_vals['state']
                                #replace country
                                if 'country' in external_address_vals:
                                    external_address_vals['country_code'] = external_address_vals['country']
                                    del external_address_vals['country']                                
                                #type
                                if address_type=='shipping':
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
                                if address_type=='billing':
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
                                external_sale_order_id.woocommerce_state = str(message_body['status'])                            
                                #action_run (only if need)
                                external_sale_order_id.action_run()
                                #result_message
                                result_message['delete_message'] = True
                                result_message['return_body'] = {'message': 'Como ya existe, actualizamos el estado del mismo unicamente'}
                            else:
                                #create
                                external_sale_order_obj = self.env['external.sale.order'].sudo(6).create(external_sale_order_vals)
                                #update subtotal_price
                                external_sale_order_obj.subtotal_price = external_sale_order_obj.total_price-external_sale_order_obj.total_tax
                                #line_items
                                for line_item in message_body['line_items']:
                                    #vals
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
                                    #variation_id
                                    if 'variation_id' in line_item:
                                        if line_item['variation_id']!='':
                                            external_stock_picking_line_vals['external_variant_id'] = str(line_item['variation_id'])                                             
                                    #create
                                    external_stock_picking_line_obj = self.env['external.sale.order.line'].sudo(6).create(external_stock_picking_line_vals)
                                #shipping_lines
                                for shipping_line in message_body['shipping_lines']:
                                    #vals                                        
                                    external_sale_order_shipping_vals = {
                                        'external_id': str(shipping_line['id']),
                                        'currency_id': external_sale_order_obj.currency_id.id,
                                        'external_sale_order_id': external_sale_order_obj.id,
                                        'title': str(shipping_line['method_title']),
                                        'price': shipping_line['total'],
                                        'tax_amount': shipping_line['total_tax']
                                    }                                                                                    
                                    #create
                                    external_sale_order_shipping_obj = self.env['external.sale.order.shipping'].sudo(6).create(external_sale_order_shipping_vals)
                                #action_run
                                external_sale_order_obj.action_run()
                                #delete_message
                                result_message['delete_message'] = True                            
                    #logger
                    _logger.info(result_message)
                    # remove_message
                    if result_message['delete_message'] == True:
                        response_delete_message = sqs.delete_message(
                            QueueUrl=sqs_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )