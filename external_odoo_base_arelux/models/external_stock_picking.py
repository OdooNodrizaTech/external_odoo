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
from woocommerce import API

class ExternalStockPicking(models.Model):
    _inherit = 'external.stock.picking'             
        
    woocommerce_update = fields.Boolean(
        string='Woocommerce Update'
    )
    
    @api.one
    def action_run(self):
        return_item = super(ExternalStockPicking, self).action_run()        
        #picking
        if self.picking_id.id>0:
            #ar_qt
            self.picking_id.ar_qt_activity_type = 'arelux'
            self.picking_id.ar_qt_customer_type = 'particular'
            #carrier_id (nacex only if 1kg)
            if self.picking_id.weight<=1: 
                delivery_carrier_ids = self.env['delivery.carrier'].sudo().search([('carrier_type', '=', 'nacex')])
                if len(delivery_carrier_ids)>0:
                    delivery_carrier_id = delivery_carrier_ids[0]
                    self.picking_id.carrier_id = delivery_carrier_id.id#Nacex 
        #return
        return return_item
        
    @api.multi
    def cron_external_stock_picking_orache_update_shipping_expedition(self, cr=None, uid=False, context=None):
        _logger.info('cron_external_stock_picking_orache_update_shipping_expedition')
        #params        
        api_orache_url = str(self.env['ir.config_parameter'].sudo().get_param('api_orache_url'))
        api_orache_consumer_key = str(self.env['ir.config_parameter'].sudo().get_param('api_orache_consumer_key'))
        api_orache_consumer_secret = str(self.env['ir.config_parameter'].sudo().get_param('api_orache_consumer_secret'))
        #search
        external_stock_picking_ids = self.env['external.stock.picking'].sudo().search(
            [                
                ('source', '=', 'woocommerce'),                
                ('source_url', 'like', 'orache'),
                ('woocommerce_update', '=', False),
                ('picking_id', '!=', False),
                ('picking_id.state', '=', 'done'),
                ('picking_id.shipping_expedition_id', '!=', False),
                ('picking_id.shipping_expedition_id.state', '=', 'delivered')
            ]
        )
        if len(external_stock_picking_ids)>0:
            #wcapi
            wcapi = API(
                url=str(api_orache_url),
                consumer_key=api_orache_consumer_key,
                consumer_secret=api_orache_consumer_secret,
                wp_api=True,
                version="wc/v3"
            )
            #operations
            for external_stock_picking_id in external_stock_picking_ids:
                _logger.info(external_stock_picking_id.id)
                _logger.info(external_stock_picking_id.number)
                #put
                data = {"status": "completed"}                
                response_wcapi = wcapi.put("orders/"+external_stock_picking_id.number, data).json()
                _logger.info('response_wcapi')
                _logger.info(response_wcapi)        