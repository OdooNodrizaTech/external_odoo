# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalStockPicking(models.Model):
    _name = 'external.stock.picking'
    _description = 'External Stock Picking'
    _order = 'create_date desc'
    
    name = fields.Char(        
        compute='_get_name',
        string='Nombre',
        store=False
    )
    
    @api.one        
    def _get_name(self):            
        for obj in self:
            obj.name = obj.external_id    
    #fields    
    woocommerce_state = fields.Selection(
        [
            ('none', 'None'),
            ('pending', 'Pending Payment'),
            ('shipped', 'Shipped'),
            ('processing', 'Processing'),
            ('on-hold', 'On Hold'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('refunded', 'Refunded'),
            ('failed', 'Failed')
        ],
        string='Woocommerce State',
        default='none'
    )
    external_id = fields.Char(
        string='External Id'
    )
    external_customer_id = fields.Many2one(
        comodel_name='external.customer',
        string='Customer'
    )
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='Source'
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
    external_stock_picking_line_ids = fields.One2many('external.stock.picking.line', 'external_stock_picking_id', string='Lines', copy=True)        

    @api.multi
    def action_run_multi(self):
        for obj in self:
            if obj.picking_id.id==0:
                obj.action_run()

    @api.one
    def allow_create(self):
        return_item = False        
        #operations
        if self.external_source_id.id>0:
            if self.external_source_id.type=='woocommerce':
                if self.woocommerce_state in ['processing', 'shipped', 'completed']:
                    return_item = True
        #return
        return return_item
        
    @api.one
    def action_run(self):
        #allow_create
        allow_create_item = self.allow_create()[0]
        if allow_create_item==True:
            self.action_stock_picking_create()
        
    @api.one
    def action_stock_picking_create(self):
        if self.picking_id.id==0:
            #allow_create
            allow_create_stock_picking = False
            if self.external_customer_id.id>0:
                if self.external_customer_id.partner_id.id>0:
                    allow_create_stock_picking = True
                    #check_external_stock_picking_line_ids                                    
                    for external_stock_picking_line_id in self.external_stock_picking_line_ids:
                        if external_stock_picking_line_id.external_product_id.id==0:
                            allow_create_stock_picking = False
            #operations
            if allow_create_stock_picking==True:                                        
                #stock_picking
                stock_picking_vals = {
                    'picking_type_id' : self.external_source_id.external_stock_picking_picking_type_id.id,
                    'location_id': self.external_source_id.external_stock_picking_picking_type_id.default_location_src_id.id,
                    'location_dest_id': 9,
                    'move_type' : 'one',
                    'partner_id': self.external_customer_id.partner_id.id,
                    'move_lines': []             
                }
                #carrier_id
                if self.external_source_id.external_stock_picking_carrier_id.id>0:
                    stock_picking_vals['carrier_id'] = self.external_source_id.external_stock_picking_carrier_id.id
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