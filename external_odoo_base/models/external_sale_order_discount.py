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

class ExternalSaleOrderDiscount(models.Model):
    _name = 'external.sale.order.discount'
    _description = 'External Sale Order Discount'
    _order = 'create_date desc'

    external_id = fields.Char(
        string='External Id'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency'
    )
    type = fields.Selection(
        [
            ('manual', 'Manual'),
        ],
        string='Type',
        default='manual'
    )
    value = fields.Monetary(
        string='Value'
    )
    value_type = fields.Selection(
        [
            ('fixed_amount', 'Fixed Amount'),
        ],
        string='Value type',
        default='fixed_amount'
    )
    description = fields.Char(
        string='Description'
    )
    title = fields.Char(
        string='Title'
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
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalSaleOrderDiscount, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item