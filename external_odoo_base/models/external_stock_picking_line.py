# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)


class ExternalStockPickingLine(models.Model):
    _name = 'external.stock.picking.line'
    _description = 'External Stock Picking Line'
    _order = 'create_date desc'
    _rec_name = 'line_id'

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

    @api.multi
    @api.depends('external_product_id', 'external_stock_picking_id')
    def operations_item(self):
        for item in self:
            if item.external_variant_id:
                items = self.env['external.product'].sudo().search(
                    [
                        ('external_source_id', '=',
                         item.external_stock_picking_id.external_source_id.id),
                        ('external_id', '=', str(item.external_id)),
                        ('external_variant_id', '=',
                         str(item.external_variant_id))
                    ]
                )
            else:
                items = self.env['external.product'].sudo().search(
                    [
                        ('external_source_id', '=',
                         item.external_stock_picking_id.external_source_id.id),
                        ('external_id', '=', str(item.external_id))
                    ]
                )
            # operations
            if items:
                _logger.info(
                    _('Very strange, external_product_id not found regarding '
                      'external_source_id=%s, external_id=%s and '
                      'external_variant_id=%s') %
                    (
                        item.external_stock_picking_id.external_source_id.id,
                        item.external_id,
                        item.external_variant_id
                    )
                )
            else:
                item.external_product_id = items[0].id
                # re-define quantity (ONLY in creation)
                item.quantity = (item.quantity * item.external_product_id.quantity_every_unit)
        # return
        return False

    @api.model
    def create(self, values):
        return_item = super(ExternalStockPickingLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item
