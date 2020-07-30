# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import Warning as UserError

import logging
_logger = logging.getLogger(__name__)


class ExternalSource(models.Model):
    _name = 'external.source'
    _description = 'External Source'

    name = fields.Char(
        string='Name'
    )
    type = fields.Selection(
        [
            ('custom', 'Custom'),
            ('shopify', 'Shopify'),
            ('woocommerce', 'Woocommerce'),
        ],
        string='Type',
        default='custom'
    )
    url = fields.Char(
        string='Url'
    )
    external_sale_order_user_id = fields.Many2one(
        comodel_name='res.users',
        string='User id',
        help='User id (external.sale.order)',
    )
    external_sale_order_account_payment_mode_id = fields.Many2one(
        comodel_name='account.payment.mode',
        string='Payment mode id',
        help='Payment mode id (external.sale.order)'
    )
    external_sale_order_account_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment term id',
        help='Payment term id (external.sale.order)'
    )
    external_sale_order_shipping_product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template id',
        help='Product Template id (external.sale.order.shipping)',
    )
    external_sale_order_carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string='Delivery Carrier Id',
        help='Delivery Carrier Id (external.sale.order)'
    )
    external_sale_order_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Stock Picking Type Id',
        help='Stock Picking Type Id (external.sale.order)',
    )
    external_sale_payment_acquirer_id = fields.Many2one(
        comodel_name='payment.acquirer',
        string='Payment Acquirer Id',
        help='Payment Acquirer Id (external.sale.order)'
    )
    external_stock_picking_user_id = fields.Many2one(
        comodel_name='res.users',
        string='User id',
        help='User id (external.stock.picking)',
    )
    external_stock_picking_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Stock Picking Type Id',
        help='Stock Picking Type Id (external.stock.picking)',
    )
    external_stock_picking_carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string='Delivery Carrier Id',
        help='Delivery Carrier Id (external.stock.picking)'
    )
    invoice_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner Id',
        help='Partner id (Auto-invoice in stock.picking)'
    )
    invoice_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal Id',
        help='Journal id (Auto-invoice in stock.picking)'
    )
    api_status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('valid', 'Valid')
        ],
        string='Api Status',
        default='draft'
    )
    api_key = fields.Char(
        string='Api Key'
    )
    api_secret = fields.Char(
        string='Api Secret'
    )

    @api.multi
    def action_api_status_draft_multi(self):
        for item in self:
            if item.api_status == 'valid':
                item.action_api_status_draft()

    @api.multi
    def action_api_status_draft(self):
        for item in self:
            item.api_status = 'draft'

    @api.multi
    def action_api_status_valid_multi(self):
        for item in self:
            if item.api_status == 'draft':
                if item.url and item.api_key and item.api_secret:
                    res = item.action_api_status_valid()
                    if not res:
                        raise UserError(
                            _('Integration with API could not be '
                              'validated (perhaps not yet available)')
                        )
                    else:
                        item.api_status = 'valid'
                else:
                    raise UserError(
                        _('The api_key and api_secret fields are required')
                    )

    @api.multi
    def action_api_status_valid(self):
        return super(ExternalSource, self).action_api_status_valid()

    @api.multi
    def action_operations_get_products_multi(self):
        for item in self:
            if item.api_key and item.api_secret:
                item.action_operations_get_products()

    @api.multi
    def action_operations_get_products(self):
        return False

    @api.model
    def cron_external_stock_picking_line_generate_invoice_lines(self):
        _logger.info('cron_external_stock_picking_line_generate_invoice_lines')
        # source
        source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'woocommerce'),
                ('invoice_partner_id', '!=', False),
                ('invoice_journal_id', '!=', False)
            ]
        )
        if source_ids:
            for source_id in source_ids:
                # external_stock_picking_line_ids
                line_ids = self.env['external.stock.picking.line'].sudo().search(
                    [
                        ('external_source_id', '=', source_id.id),
                        ('invoice_line_id', '=', False),
                        ('external_stock_picking_id.picking_id', '!=', False),
                        ('external_stock_picking_id.picking_id.state', '=', 'done'),
                        ('external_product_id', '!=', False),
                        ('external_product_id.invoice_partner_id', '!=', False)
                    ]
                )
                if line_ids:
                    # search draft invoice
                    invoice_ids = self.env['account.invoice'].sudo().search(
                        [
                            ('partner_id', '=', source_id.invoice_partner_id.id),
                            ('state', '=', 'draft'),
                            ('type', '=', 'out_invoice'),
                            ('journal_id', '=', source_id.invoice_journal_id.id)
                        ]
                    )
                    if invoice_ids:
                        invoice_id = invoice_ids[0]
                    else:
                        # create_proccess
                        vals = {
                            'partner_id': source_id.invoice_partner_id.id,
                            'partner_shipping_id': source_id.invoice_partner_id.id,
                            'state': 'draft',
                            'type': 'out_invoice',
                            'journal_id': source_id.invoice_journal_id.id,
                            'user_id': 0
                        }
                        # property_payment_term_id
                        if source_id.invoice_partner_id.property_payment_term_id:
                            vals['payment_term_id'] = \
                                source_id.invoice_partner_id.property_payment_term_id.id
                        # customer_payment_mode_id
                        if source_id.invoice_partner_id.customer_payment_mode_id:
                            vals['payment_mode_id'] = \
                                source_id.invoice_partner_id.customer_payment_mode_id.id
                        # create
                        obj = self.env['account.invoice'].create(vals)
                        invoice_id = obj
                    # add_lines
                    for line_id in line_ids:
                        # vals
                        line_vals = {
                            'invoice_id': invoice_id.id,
                            'product_id':
                                line_id.external_product_id.product_template_id.id,
                            'name': '%s (%s)' % (
                                line_id.title,
                                line_id.external_stock_picking_id.picking_id.name
                            ),
                            'quantity': line_id.quantity,
                            'price_unit':
                                line_id.external_product_id.product_template_id.list_price,
                            'currency_id': account_invoice_id.currency_id.id,                        
                        }
                        # account_id
                        if line_id.external_product_id.\
                                product_template_id.property_account_income_id:
                            line_vals['account_id'] = \
                                line_id.external_product_id.\
                                    product_template_id.property_account_income_id.id
                        else:
                            line_vals['account_id'] = \
                                line_id.external_product_id.product_template_id.\
                                    categ_id.property_account_income_categ_id.id
                        # create
                        obj = self.env['account.invoice.line'].create(line_vals)
                        # onchange
                        obj._onchange_product_id()
                        obj._onchange_account_id()
                        obj.name = '%s (%s)' % (
                            line_id.title,
                            line_id.external_stock_picking_id.picking_id.name
                        )
                        # update
                        line_id.invoice_line_id = obj.id
