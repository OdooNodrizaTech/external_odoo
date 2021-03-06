# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
                if item.external_sale_order_id:
                    if item.external_sale_order_id.external_source_id:
                        for picking_id in item.picking_ids:
                            item_es = item.external_sale_order_id.external_source_id
                            item_es_esopt = item_es.external_sale_order_picking_type_id
                            if picking_id.picking_type_id.id != item_es_esopt.id:
                                picking_id.picking_type_id = item_es_esopt.id
                                picking_id.name = self.env['ir.sequence'].next_by_code(
                                    self.env['stock.picking.type'].search(
                                        [
                                            ('id', '=', picking_id.picking_type_id.id)
                                        ]
                                    )[0].sequence_id.code
                                )
        # return
        return return_action
