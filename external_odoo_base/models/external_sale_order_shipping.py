# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class ExternalSaleOrderShipping(models.Model):
    _name = 'external.sale.order.shipping'
    _description = 'External Sale Order Shipping'
    _order = 'create_date desc'

    external_id = fields.Char(
        string='External Id'
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency'
    )
    title = fields.Char(
        string='Title'
    )
    price = fields.Monetary(
        string='Price'
    )
    discounted_price = fields.Monetary(
        string='Discounted Price'
    )
    tax_amount = fields.Monetary(
        string='Tax Amount'
    )
    unit_price_without_tax = fields.Float(
        string='Unit price Without Tax',
        digits=dp.get_precision('Price Unit'),
        help='Calculate (total_price_without_tax/quantity)'
    )
    total_price_without_tax = fields.Monetary(
        string='Total price Without Tax'
    )
    external_sale_order_id = fields.Many2one(
        comodel_name='external.sale.order',
        string='Sale Order',
        ondelete='cascade'
    )
    sale_order_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='sale_order_line'
    )

    @api.multi
    def operations_item(self):
        for item in self:
            # calculate_tax
            if item.tax_amount > 0:
                item.total_price_without_tax = item.price-item.tax_amount
                item.unit_price_without_tax = item.total_price_without_tax / 1
        # return
        return False

    @api.model
    def create(self, values):
        return_item = super(ExternalSaleOrderShipping, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item
