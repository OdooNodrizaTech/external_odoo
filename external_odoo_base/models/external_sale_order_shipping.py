# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalSaleOrderShipping(models.Model):
    _name = 'external.sale.order.shipping'
    _description = 'External Sale Order Shipping'
    _order = 'create_date desc'

    external_id = fields.Char(
        string='External Id'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency'
    )
    title = fields.Char(
        string='Title'
    )
    price = fields.Monetary(
        string='Price'
    )
    discounted_price = fields.Monetary(
        string='Discounted Price'
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
    external_sale_order_id = fields.Many2one(
        comodel_name='external.sale.order',
        string='External Sale Order',
        ondelete='cascade'
    )
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Sale Order Line'
    )  

    @api.one
    def operations_item(self):
        #calculate_tax
        if self.tax_amount>0:
            self.total_price_without_tax = self.price-self.tax_amount
            self.unit_price_without_tax = self.total_price_without_tax/1
        #return
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalSaleOrderShipping, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item