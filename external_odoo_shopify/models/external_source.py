# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.exceptions import Warning

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
            #shopify api (not work)
            '''
            session = shopify.Session(self.url, '2020-01')                                
            token = session.request_token(params)
            self.shopify_access_token = str(token)
            #session
            session = shopify.Session(self.url, '2020-01', self.shopify_access_token)
            shopify.ShopifyResource.activate_session(session)
            '''            
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
                                inventory_level = shopify.InventoryLevel.set(location_id=42284515467, inventory_item_id=variant.inventory_item_id, available=int(qty_item), disconnect_if_necessary=False)