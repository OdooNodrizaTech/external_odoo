# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalStockPickingLine(models.Model):
    _name = 'external.stock.picking.line'
    _description = 'External Stock Picking Line'
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
        string='Id (Product id)'
    )
    external_variant_id = fields.Char(
        string='Variant Id (Variant Id)'
    )
    external_product_id = fields.Many2one(
        comodel_name='external.product',
        string='Product'
    )
    external_stock_picking_id = fields.Many2one(
        comodel_name='external.stock.picking',
        string='Sale Order',
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
        string='move_id'
    )
    invoice_line_id = fields.Many2one(
        comodel_name='account.invoice.line',
        string='invoice_line_id'
    )        

    @api.one
    def operations_item(self):
        if self.external_product_id.id==0:
            if self.external_stock_picking_id.id>0:
                if self.external_variant_id!=False:
                    external_product_ids = self.env['external.product'].sudo().search(
                        [
                            ('external_source_id', '=', self.external_stock_picking_id.external_source_id.id),
                            ('external_id', '=', str(self.external_id)),
                            ('external_variant_id', '=', str(self.external_variant_id))
                        ]
                    )
                else:
                    external_product_ids = self.env['external.product'].sudo().search(
                        [
                            ('external_source_id', '=', self.external_stock_picking_id.external_source_id.id),
                            ('external_id', '=', str(self.external_id))
                        ]
                    )
                # operations
                if len(external_product_ids)==0:
                    _logger.info('Muy raro, no se encuentra external_product_id respecto a external_source_id='+str(self.external_stock_picking_id.external_source_id.id)+', external_id='+str(self.external_id)+' y external_variant_id='+str(self.external_variant_id))
                else:
                    external_product_id = external_product_ids[0]
                    self.external_product_id = external_product_id.id
                    # re-define quantity (ONLY in creation)
                    item.quantity = (item.quantity * item.external_product_id.quantity_every_unit)
        #return
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalStockPickingLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item