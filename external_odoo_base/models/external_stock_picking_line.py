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

class ExternalStockPickingLine(models.Model):
    _name = 'external.stock.picking.line'
    _description = 'External Stock Picking Line'
    _order = 'create_date desc'
    
    line_id = fields.Char(
        string='Line Id'
    )
    external_id = fields.Char(
        string='External Id (Product id)'
    )
    external_variant_id = fields.Char(
        string='External Variant Id'
    )
    external_product_id = fields.Many2one(
        comodel_name='external.product',
        string='External Product'
    )
    external_stock_picking_id = fields.Many2one(
        comodel_name='external.stock.picking',
        string='External Sale Order',
        ondelete='cascade'
    )    
    title = fields.Char(
        string='Title'
    )
    quantity = fields.Integer(
        string='Quantity'
    )    
    move_id = fields.Many2one(
        comodel_name='stock.move',
        string='Stock Move'
    )
    invoice_line_id = fields.Many2one(
        comodel_name='account.invoice.line',
        string='Account Invoice Line'
    )        

    @api.one
    def operations_item(self):
        if self.external_product_id.id==0:
            if self.external_stock_picking_id.id>0:
                external_product_ids = self.env['external.product'].sudo().search(
                    [
                        ('source', '=', str(self.external_stock_picking_id.source)),
                        ('external_id', '=', str(self.external_id)),
                        ('external_variant_id', '=', str(self.external_variant_id))
                    ]
                )
                if len(external_product_ids)>0:
                    external_product_id = external_product_ids[0]
                    self.external_product_id = external_product_id.id
        #return
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalStockPickingLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item
        
    @api.multi
    def cron_external_stock_picking_line_generate_invoice_lines(self, cr=None, uid=False, context=None):
        _logger.info('cron_external_stock_picking_line_generate_invoice_lines')        