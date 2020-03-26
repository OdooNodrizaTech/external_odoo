# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalSaleOrderLine(models.Model):
    _name = 'external.sale.order.line'
    _description = 'External Sale Order Line'
    _order = 'create_date desc'
    
    line_id = fields.Char(
        string='Line Id'
    )
    external_id = fields.Char(
        string='External Id (Product_id)'
    )
    external_variant_id = fields.Char(
        string='External Variant Id (Variant_id)'
    )
    external_product_id = fields.Many2one(
        comodel_name='external.product',
        string='External Product'
    )
    external_sale_order_id = fields.Many2one(
        comodel_name='external.sale.order',
        string='External Sale Order',
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
        string='Price'
    )
    total_discount = fields.Monetary(
        string='Total Discount'
    )
    tax_amount = fields.Monetary(
        string='Tax Amount'
    )
    unit_price_without_tax = fields.Monetary(
        string='Unit price Without Tax'
    )
    total_price_without_tax = fields.Monetary(
        string='Total price Without Tax'
    ) 
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Sale Order Line'
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
            self.total_price_without_tax = self.price-self.tax_amount
            self.unit_price_without_tax = self.total_price_without_tax
        #return
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalSaleOrderLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item