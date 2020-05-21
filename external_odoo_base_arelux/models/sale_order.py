# -*- coding: utf-8 -*-
from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
       # operations
        for item in self:
            if item.state == 'sale':
                for picking_id in item.picking_ids:
                    if item.external_sale_order_id.id > 0:
                        if item.external_sale_order_id.external_source_id.id > 0:
                            for picking_id in item.picking_ids:
                                if picking_id.picking_type_id.id != item.external_sale_order_id.external_source_id.external_sale_order_picking_type_id.id:
                                    picking_id.picking_type_id = item.external_sale_order_id.external_source_id.external_sale_order_picking_type_id.id
                                    picking_id.name = self.env['ir.sequence'].next_by_code(self.env['stock.picking.type'].search([('id', '=', picking_id.picking_type_id.id)])[0].sequence_id.code)
        # return
        return return_data