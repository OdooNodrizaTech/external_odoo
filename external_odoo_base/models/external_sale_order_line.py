# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
import odoo.addons.decimal_precision as dp

class ExternalSaleOrderLine(models.Model):
    _name = 'external.sale.order.line'
    _description = 'External Sale Order Line'
    _order = 'create_date desc'
    
    name = fields.Char(        
        compute='_get_name',
        string='Nombre',
        store=False
    )
    
    @api.one        
    def _get_name(self):            
        for obj in self:
            obj.name = obj.line_id
    #fields
    line_id = fields.Char(
        string='Line Id'
    )
    external_id = fields.Char(
        string='Id (Product_id)'
    )
    external_variant_id = fields.Char(
        string='Variant Id (Variant_id)'
    )
    external_product_id = fields.Many2one(
        comodel_name='external.product',
        string='Product'
    )
    external_sale_order_id = fields.Many2one(
        comodel_name='external.sale.order',
        string='Sale Order',
        ondelete='cascade'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency'
    )
    title = fields.Char(
        string='Title'
    )
    quantity = fields.Integer(
        string='Quantity'
    )
    sku = fields.Char(
        string='Sku'
    )
    price = fields.Monetary(
        string='Price',
        help='Unit price (with tax)'
    )
    total_discount = fields.Monetary(
        string='Total Discount'
    )
    tax_amount = fields.Monetary(
        string='Tax Amount',
        help='Total tax amount (line)'
    )
    unit_price_without_tax = fields.Float(
        string='Unit price Without Tax',
        digits=dp.get_precision('Price Unit'),        
        help='Calculate (total_price_without_tax/quantity)'
    )
    total_price_without_tax = fields.Monetary(
        string='Total price Without Tax',
        help='Calculate (price*quantity)-tax_amount'
    ) 
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='sale_order_line'
    )        

    @api.one
    def operations_item(self):
        #external_product_id
        if self.external_product_id.id==0:
            if self.external_sale_order_id.id>0:
                if self.external_variant_id!=False:
                    external_product_ids = self.env['external.product'].sudo().search(
                        [
                            ('external_source_id', '=', self.external_sale_order_id.external_source_id.id),
                            ('external_id', '=', str(self.external_id)),
                            ('external_variant_id', '=', str(self.external_variant_id))
                        ]
                    )
                else:
                    external_product_ids = self.env['external.product'].sudo().search(
                        [
                            ('external_source_id', '=', self.external_sale_order_id.external_source_id.id),
                            ('external_id', '=', str(self.external_id))
                        ]
                    )
                #operations                                          
                if len(external_product_ids)==0:
                    _logger.info('Muy raro, no se encuentra external_product_id respecto a external_source_id='+str(self.external_sale_order_id.external_source_id.id)+', external_id='+str(self.external_id)+' y external_variant_id='+str(self.external_variant_id))
                else:
                    external_product_id = external_product_ids[0]
                    self.external_product_id = external_product_id.id
        #calculate_tax
        if self.tax_amount>0:
            self.total_price_without_tax = (self.price*self.quantity)-self.tax_amount
            self.unit_price_without_tax = self.total_price_without_tax/self.quantity            
        #return
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalSaleOrderLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item