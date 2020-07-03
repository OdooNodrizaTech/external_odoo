# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import dateutil.parser

import boto3
from botocore.exceptions import ClientError
import shopify
import urlparse

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
                params_urlparse = urlparse.parse_qs(parsed.query)
                if len(params_urlparse) > 0:
                    for param_urlparse in params_urlparse:
                        params[str(param_urlparse)] = str(params_urlparse[param_urlparse][0])
                #landing_url
                self.landing_url = parsed.path
                #utm_campaign
                if 'utm_campaign' in params:
                    self.landing_utm_campaign = params['utm_campaign']
                #utm_medium
                if 'utm_medium' in params:
                    self.landing_utm_medium = params['utm_medium']
                #utm_source
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
    
    @api.multi
    def cron_external_sale_order_update_shipping_expedition_shopify(self, cr=None, uid=False, context=None):
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

    @api.multi
    def cron_sqs_external_sale_order_shopify(self, cr=None, uid=False, context=None):
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
                            result_message = external_source_id.generate_external_sale_order_shopify(message_body)[0]
                    #logger
                    _logger.info(result_message)                                                            
                    # remove_message
                    if result_message['delete_message']==True:
                        response_delete_message = sqs.delete_message(
                            QueueUrl=sqs_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )