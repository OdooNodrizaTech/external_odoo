# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
_logger = logging.getLogger(__name__)

from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    external_sale_order_id = fields.Many2one(
        comodel_name='external.sale.order',
        string='External Sale Order Id'
    )

    @api.multi
    def action_confirm(self):
        return_action = super(SaleOrder, self).action_confirm()
        # operations
        for item in self:
            if item.state == 'sale':
                if item.external_sale_order_id.id > 0:
                    if item.external_sale_order_id.external_source_id.id > 0:
                        for picking_id in item.picking_ids:
                            if picking_id.picking_type_id.id != item.external_sale_order_id.external_source_id.external_sale_order_picking_type_id.id:
                                picking_id.picking_type_id = item.external_sale_order_id.external_source_id.external_sale_order_picking_type_id.id
                                picking_id.name = self.env['ir.sequence'].next_by_code(
                                    self.env['stock.picking.type'].search([('id', '=', picking_id.picking_type_id.id)])[
                                        0].sequence_id.code)
        # return
        return return_action