# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)


class ExternalSaleOrderLine(models.Model):
    _name = 'external.sale.order.line'
    _description = 'External Sale Order Line'
    _order = 'create_date desc'
    _rec_name = 'line_id'

    line_id = fields.Char(
        string='Line Id'
    )
    external_id = fields.Char(
        string='Id (Product_id)'
    )
    external_variant_id = fields.Char(
        string='Variant Id (Variant_id)'
    )
    external_product_id = fields.Many2one(
        comodel_name='external.product',
        string='Product'
    )
    external_sale_order_id = fields.Many2one(
        comodel_name='external.sale.order',
        string='Sale Order',
        ondelete='cascade'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency'
    )
    title = fields.Char(
        string='Title'
    )
    quantity = fields.Integer(
        string='Quantity'
    )
    sku = fields.Char(
        string='Sku'
    )
    price = fields.Monetary(
        string='Price',
        help='Unit price (with tax)'
    )
    total_discount = fields.Monetary(
        string='Total Discount'
    )
    tax_amount = fields.Monetary(
        string='Tax Amount',
        help='Total tax amount (line)'
    )
    unit_price_without_tax = fields.Float(
        string='Unit price Without Tax',
        digits=dp.get_precision('Price Unit'),
        help='Calculate (total_price_without_tax/quantity)'
    )
    total_price_without_tax = fields.Monetary(
        string='Total price Without Tax',
        help='Calculate (price*quantity)-tax_amount'
    )
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='sale_order_line'
    )

    @api.multi
    @api.depends('external_product_id', 'external_sale_order_id')
    def operations_item(self):
        for item in self:
            if item.external_variant_id:
                items = self.env['external.product'].sudo().search(
                    [
                        ('external_source_id', '=',
                         item.external_sale_order_id.external_source_id.id),
                        ('external_id', '=', str(item.external_id)),
                        ('external_variant_id', '=', str(item.external_variant_id))
                    ]
                )
            else:
                items = self.env['external.product'].sudo().search(
                    [
                        ('external_source_id', '=',
                         item.external_sale_order_id.external_source_id.id),
                        ('external_id', '=', str(item.external_id))
                    ]
                )
            # operations
            if items:
                item.external_product_id = items[0].id
            else:
                _logger.info(
                    _('Very strange, external_product_id not found regarding'
                      ' external_source_id=%s, external_id=%s and external_'
                      'variant_id=%s')
                    % (
                        self.external_sale_order_id.external_source_id.id,
                        self.external_id,
                        self.external_variant_id
                    )
                )
            # calculate_tax
            if item.tax_amount > 0:
                item.total_price_without_tax = \
                    (item.price*item.quantity)-item.tax_amount
                item.unit_price_without_tax = \
                    item.total_price_without_tax/item.quantity
        # return
        return False

    @api.model
    def create(self, values):
        return_item = super(ExternalSaleOrderLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item
