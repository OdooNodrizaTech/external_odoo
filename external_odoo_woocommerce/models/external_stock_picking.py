# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from odoo import api, models, tools, _

import json
import boto3
_logger = logging.getLogger(__name__)


class ExternalStockPicking(models.Model):
    _inherit = 'external.stock.picking'

    @api.multi
    def action_run(self):
        return_item = super(ExternalStockPicking, self).action_run()
        return return_item

    @api.model
    def cron_external_stock_picking_update_shipping_expedition_woocommerce(self):
        # search
        source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'woocommerce'),
                ('api_status', '=', 'valid')
            ]
        )
        if source_ids:
            for source_id in source_ids:
                # external_stock_picking_ids
                picking_ids = self.env['external.stock.picking'].sudo().search(
                    [
                        ('external_source_id', '=', source_id.id),
                        ('woocommerce_state', 'in', ('processing', 'shipped')),
                        ('picking_id', '!=', False),
                        ('picking_id.state', '=', 'done'),
                        ('picking_id.shipping_expedition_id', '!=', False),
                        ('picking_id.shipping_expedition_id.state', '=', 'delivered')
                    ]
                )
                if picking_ids:
                    # wcapi (init)
                    wcapi = source_id.init_api_woocommerce()[0]
                    # operations
                    for picking_id in picking_ids:
                        # put
                        data = {"status": "completed"}
                        response = wcapi.put(
                            "orders/%s" % picking_id.number,
                            data
                        ).json()
                        if 'id' in response:
                            # update OK
                            picking_id.woocommerce_state = 'completed'

    @api.model
    def cron_sqs_external_stock_picking_woocommerce(self):
        sqs_url = tools.config.get('sqs_external_stock_picking_woocommerce_url')
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
                    # message_body
                    _logger.info(message_body)
                    # result_message
                    result_message = {
                        'statusCode': 200,
                        'return_body': 'OK',
                        'delete_message': False,
                        'message': message_body
                    }
                    # line_items
                    if 'line_items' not in message_body:
                        result_message['statusCode'] = 500
                        result_message['delete_message'] = True
                        result_message['return_body'] = {
                            'error': _('Line_items field missing')
                        }
                    # default
                    source = 'woocommerce'
                    # fields_need_check
                    fields_need_check = [
                        'status', 'shipping', 'billing', 'X-WC-Webhook-Source'
                    ]
                    for fnc in fields_need_check:
                        if fnc not in message_body:
                            result_message['statusCode'] = 500
                            result_message['delete_message'] = True
                            result_message['return_body'] = \
                                _('The field does not exist %s') % fnc
                    # operations_1
                    if result_message['statusCode'] == 200:
                        # source_url
                        source_url = str(message_body['X-WC-Webhook-Source'])
                        # external_source_id
                        source_ids = self.env['external.source'].sudo().search(
                            [
                                ('type', '=', str(source))
                                ('url', '=', str(source_url))
                            ]
                        )
                        if len(source_ids) == 0:
                            result_message['statusCode'] = 500
                            result_message['return_body'] = {
                                'error': _(
                                    'External_source id does not exist '
                                    'with this source=%s and url =%s'
                                ) % (source, source_url)
                            }
                        else:
                            source_id = source_ids[0]
                        # status
                        if message_body['status'] not in [
                            'processing', 'completed', 'shipped', 'refunded'
                        ]:
                            result_message['statusCode'] = 500
                            result_message['delete_message'] = True
                            result_message['return_body'] = {
                                'error': _('The order is not completed')
                            }
                        # create-write
                        if result_message['statusCode'] == 200:  # error, data not exists
                            res = source_id.generate_external_stock_picking_woocommerce(
                                message_body
                            )[0]
                            result_message = res
                    # logger
                    _logger.info(result_message)                                                            
                    # remove_message
                    if result_message['delete_message']:
                        sqs.delete_message(
                            QueueUrl=sqs_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
