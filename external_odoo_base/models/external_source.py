# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.exceptions import Warning

class ExternalSource(models.Model):
    _name = 'external.source'
    _description = 'External Source'

    name = fields.Char(
        string='Name'
    )                        
    type = fields.Selection(
        [
            ('custom', 'Custom'),
            ('shopify', 'Shopify'),
            ('woocommerce', 'Woocommerce'),
        ],
        string='Type',
        default='custom'
    )
    url = fields.Char(
        string='Url'
    )
    external_sale_order_user_id = fields.Many2one(
        comodel_name='res.users',
        string='User id',
        help='User id (external.sale.order)',
    )
    external_sale_order_account_payment_mode_id = fields.Many2one(
        comodel_name='account.payment.mode',
        string='Payment mode id',
        help='Payment mode id (external.sale.order)'
    )
    external_sale_order_account_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment term id',
        help='Payment term id (external.sale.order)'
    )
    external_sale_order_shipping_product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template id',
        help='Product Template id (external.sale.order.shipping)',
    )
    external_stock_picking_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Stock Picking Type Id',
        help='Stock Picking Type Id (external.stock.picking)',
    )
    external_stock_picking_carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string='Delivery Carrier Id',
        help='Delivery Carrier Id (external.stock.picking)'
    )
    api_status = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('valid', 'Valida')
        ],
        string='Api Status',
        default='draft'
    )
    api_key = fields.Char(
        string='Api Key'
    )
    api_secret = fields.Char(
        string='Api Secret'
    )
        
    @api.multi
    def action_api_status_draft_multi(self):
        for obj in self:
            if obj.api_status=='valid':
                obj.api_status = 'draft'
    
    @api.multi
    def action_api_status_valid_multi(self):
        for obj in self:
            if obj.api_status=='draft':
                if obj.url!=False and obj.api_key!=False and obj.api_secret!=False:
                    return_item = obj.action_api_status_valid()
                    if return_item==False:
                        raise Warning("No se ha podido validar la integracion con la API (quizas no esta disponible todavia)")
                    else:
                        obj.api_status = 'valid'
                else:
                    raise Warning("Los campos de api_key y api_secret son necesarios")                        
                    
                    
    @api.one
    def action_api_status_valid(self):
        return super(ExternalSource, self).action_api_status_valid()                    
        
    @api.multi
    def action_operations_get_products_multi(self):
        for obj in self:
            if obj.api_key!=False and obj.api_secret!=False:
                obj.action_operations_get_products()                
        
    @api.one
    def action_operations_get_products(self):
        return False                                            