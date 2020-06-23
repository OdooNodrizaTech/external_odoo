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
                        #operations_update