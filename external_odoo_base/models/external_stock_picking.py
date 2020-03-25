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

class ExternalStockPicking(models.Model):
    _name = 'external.stock.picking'
    _description = 'External Stock Picking'
    _order = 'create_date desc'    
    #fields
    state = fields.Char(
        string='State'
    )
    external_id = fields.Char(
        string='External Id'
    )
    external_customer_id = fields.Many2one(
        comodel_name='external.customer',
        string='External Customer'
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
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Albaran'
    )
    number = fields.Integer(
        string='Number'
    )    
    external_source_name = fields.Selection(
        [
            ('web', 'Web')
        ],
        string='External Source Name',
        default='web'
    )
    external_stock_picking_line_ids = fields.One2many('external.stock.picking.line', 'external_stock_picking_id', string='External Stock Picking Lines', copy=True)        

    @api.multi
    def action_run_multi(self):
        for obj in self:
            if obj.picking_id.id==0:
                obj.action_run_multi()

    @api.one
    def action_run(self):
        #operations
        if self.picking_id.id==0:
            if self.external_customer_id.id>0:
                if self.external_customer_id.partner_id.id>0:
                    #allow_create
                    allow_create = True
                    for external_stock_picking_line_id in self.external_stock_picking_line_ids:
                        if external_stock_picking_line_id.external_product_id.id==0:
                            allow_create = False
                    #operations
                    if allow_create==True:
                        #params
                        external_odoo_external_stock_picking_picking_type_id = int(self.env['ir.config_parameter'].sudo().get_param('external_odoo_external_stock_picking_picking_type_id'))
                        external_odoo_carrier_id = int(self.env['ir.config_parameter'].sudo().get_param('external_odoo_carrier_id'))
                        #stock_picking_type
                        stock_picking_type_id = self.env['stock.picking.type'].sudo().browse(external_odoo_external_stock_picking_picking_type_id)                    
                        #stock_picking
                        stock_picking_vals = {
                            'picking_type_id' : stock_picking_type_id.id,
                            'location_id': stock_picking_type_id.default_location_src_id.id,
                            'location_dest_id': 9,
                            'move_type' : 'one',
                            'partner_id': self.external_customer_id.partner_id.id,
                            'move_lines': []             
                        }
                        #carrier_id
                        if external_odoo_carrier_id>0:
                            stock_picking_vals['carrier_id'] = external_odoo_carrier_id
                        #move_lines
                        for external_stock_picking_line_id in self.external_stock_picking_line_ids:
                            if external_stock_picking_line_id.external_product_id.id>0:
                                move_line_item = {
                                    'product_id': external_stock_picking_line_id.external_product_id.product_template_id.id,
                                    'name': external_stock_picking_line_id.external_product_id.product_template_id.name,
                                    'product_uom_qty': external_stock_picking_line_id.quantity,
                                    'product_uom': external_stock_picking_line_id.external_product_id.product_template_id.uom_id.id,
                                    'state': 'draft',                        
                                }
                                stock_picking_vals['move_lines'].append((0, 0, move_line_item))
                        #create
                        stock_picking_obj = self.env['stock.picking'].create(stock_picking_vals)
                    #update
                    self.picking_id = stock_picking_obj.id
                    #lines
                    for move_line in stock_picking_obj.move_lines:
                        external_stock_picking_line_ids = self.env['external.stock.picking.line'].sudo().search([('external_stock_picking_id', '=', self.id),('external_product_id.product_template_id', '=', move_line.product_id.id)])
                        if len(external_stock_picking_line_ids)>0:
                            external_stock_picking_line_id = external_stock_picking_line_ids[0]
                            external_stock_picking_line_id.move_id = move_line.id         
                    #action_confirm
                    stock_picking_obj.action_confirm()
                    #force_assign
                    stock_picking_obj.force_assign()                            
        #return
        return False            