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

class ExternalSaleOrder(models.Model):
    _name = 'external.sale.order'
    _description = 'External Sale Order'
    _order = 'create_date desc'
    
    #fields
    external_id = fields.Char(
        string='External Id'
    )
    external_billing_address_id = fields.Many2one(
        comodel_name='external.address',
        string='External Billing Address'
    )
    external_shipping_address_id = fields.Many2one(
        comodel_name='external.address',
        string='External Shipping Address'
    )
    external_customer_id = fields.Many2one(
        comodel_name='external.customer',
        string='External Customer'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency'
    )        
    source = fields.Selection(
        [
            ('custom', 'Custom'),
            ('shopify', 'Shopify'),
            ('woocommerce', 'Woocommerce'),
        ],
        string='Source',
        default='custom'
    )
    source_url = fields.Char(
        string='Source Url'
    )
    payment_transaction_id = fields.Many2one(
        comodel_name='payment.transaction',
        string='Payment Transaction'
    )
    sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Pedido de venta'
    )
    number = fields.Integer(
        string='Number'
    )
    total_price = fields.Monetary(
        string='Total Price'
    )
    subtotal_price = fields.Monetary(
        string='Subtotal Price'
    )
    total_tax = fields.Monetary(
        string='Total Tax'
    )
    total_discounts = fields.Monetary(
        string='Total Discounts'
    )
    total_line_items_price = fields.Monetary(
        string='Total Line Items Price'
    )
    external_source_name = fields.Selection(
        [
            ('web', 'Web')
        ],
        string='External Source Name',
        default='web'
    )
    total_shipping_price = fields.Monetary(
        string='Total Shipping Price'
    )
    external_sale_order_discount_ids = fields.One2many('external.sale.order.discount', 'external_sale_order_id', string='External Sale Order Discounts', copy=True)
    external_sale_order_line_ids = fields.One2many('external.sale.order.line', 'external_sale_order_id', string='External Sale Order Lines', copy=True)
    external_sale_order_shipping_id = fields.Many2one(
        comodel_name='external.sale.order.shipping',
        string='External Sale Order Shipping'
    )    

    @api.one
    def action_run(self):
        return False