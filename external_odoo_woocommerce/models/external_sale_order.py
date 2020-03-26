# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

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
                        ('state', '!=', 'completed'),
                        ('sale_order_id', '!=', False),
                        ('sale_order_id.state', 'in', ('sale', 'done'))
                    ]
                )
                if len(external_sale_order_ids)>0:
                    for external_sale_order_id in external_sale_order_ids:
                        #wcapi (init)
                        wcapi = external_source_id.init_api_woocommerce()[0]
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
                                external_sale_order_id.state = 'completed'        
    
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
                    # fields_need_check
                    fields_need_check = ['name']
                    for field_need_check in fields_need_check:
                        if field_need_check not in message_body:
                            result_message['statusCode'] = 500
                            result_message['delete_message'] = True
                            result_message['return_body'] = 'No existe el campo ' + str(field_need_check)
                    # operations
                    if result_message['statusCode'] == 200:
                        #operaciones aqui para construir el SNS 'base'
                        # create-write
                        if result_message['statusCode'] == 200:  # error, data not exists
                            #enviar por SNS si todo está OK un SNS a sns_external_sale_order (pendiente de definir)
                            external_sale_order_obj = self.env['external.sale.order'].sudo().create(result_message['values'])
                            _logger.info(external_sale_order_obj)
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