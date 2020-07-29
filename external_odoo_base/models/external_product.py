# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ExternalProduct(models.Model):
    _name = 'external.product'
    _description = 'External Product'
    _order = 'create_date desc'
    _rec_name = 'external_id'

    external_id = fields.Char(
        string='External Id'
    )
    external_variant_id = fields.Char(
        string='Variant Id'
    )
    name = fields.Char(
        string='Name'
    )
    sku = fields.Char(
        string='Sku'
    )
    stock_sync = fields.Boolean(
        string='Stock Sync',
        default=False
    )
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='Source'
    )
    product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template'
    )
    external_url = fields.Char(
        compute='_compute_external_url',
        string='External Url',
        store=False
    )

    @api.multi
    @api.depends('external_source_id', 'external_id')
    def _compute_external_url(self):
        self.ensure_one()
        self.external_url = ''
        if self.external_source_id.type == 'shopify':
            self.external_url = 'https://%s/admin/products/%s' % (
                self.external_source_id.url,
                self.external_id
            )
        elif self.external_source_id.type == 'woocommerce':
            self.external_url = '%swp-admin/post.php?post=%s&action=edit' % (
                self.external_source_id.url,
                self.external_id
            )

    @api.multi
    def operations_item(self):
        self.ensure_one()
        return False

    @api.model
    def create(self, values):
        return_item = super(ExternalProduct, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item
