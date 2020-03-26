# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

from woocommerce import API

class ExternalSource(models.Model):
    _inherit = 'external.source'        
    
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
        response = wcapi.get("products").json()
        if 'message' in response:
            _logger.info('Error en la consulta')
            _logger.info(response)
        else:
            for response_item in response:
                if response_item['status']=='publish':                    
                    if len(response_item['variations'])>0:
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
                                    'external_variant_id': str(variation),
                                    'name': response_item['name'],
                                }
                                external_product_obj = self.env['external.product'].create(external_product_vals)                                                            