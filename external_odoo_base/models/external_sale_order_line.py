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

class ExternalSaleOrderLine(models.Model):
    _name = 'external.sale.order.line'
    _description = 'External Sale Order Line'
    _order = 'create_date desc'

    external_id = fields.Char(
        string='External Id'
    )
    external_variant_id = fields.Char(
        string='External Variant Id'
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
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Sale Order Line'
    )        

    @api.one
    def operations_item(self):
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalSaleOrderLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item