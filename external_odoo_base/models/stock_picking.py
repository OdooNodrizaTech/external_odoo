# -*- coding: utf-8 -*-
from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    external_stock_picking_id = fields.Many2one(
        comodel_name='external.stock.picking',
        string='External Stock Picking Id'
    )

    @api.model
    def create(self, vals):
        #check
        if 'origin' in vals:
            if 'picking_type_id' in vals:
                external_sale_order_ids = self.env['external.sale.order'].sudo().search(
                    [
                        ('sale_order_id.name', '=', str(vals['origin'])),
                        ('external_source_id.external_sale_order_picking_type_id', '!=', False),
                        ('external_source_id.external_sale_order_picking_type_id', '!=', vals['picking_type_id']),
                        ('name', '=', str(vals['origin']))
                    ]
                )
                if len(external_sale_order_ids)>0:
                    external_sale_order_id = external_sale_order_ids[0]
                    if external_sale_order_id.external_source_id.id>0:
                        if external_sale_order_id.external_source_id.external_sale_order_picking_type_id.id>0:
                            vals['picking_type_id'] = external_sale_order_id.external_source_id.external_sale_order_picking_type_id.id
                            vals['name'] = self.env['ir.sequence'].next_by_code(self.env['stock.picking.type'].search([('id', '=', vals['picking_type_id'])])[0].sequence_id.code)                            
        #create
        return_object = super(StockPicking, self).create(vals)
        #return
        return return_object