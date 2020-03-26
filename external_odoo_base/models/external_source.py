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
        string='User id (external.sale.order)'
    )
    external_sale_order_account_payment_mode_id = fields.Many2one(
        comodel_name='account.payment.mode',
        string='Payment mode id (external.sale.order)'
    )
    external_sale_order_account_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment term id (external.sale.order)'
    )
    external_sale_order_shipping_product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template id (external.sale.order.shipping)'
    )
    external_stock_picking_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Stock Picking Type Id (external.stock.picking)'
    )
    external_stock_picking_carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string='Delivery Carrier Id (external.stock.picking)'
    )        