# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ExternalStockPicking(models.Model):
    _name = 'external.stock.picking'
    _description = 'External Stock Picking'
    _order = 'create_date desc'
    _rec_name = 'external_id'

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
            self.external_url = 'https://%s/admin/orders/%s' % (
                self.external_source_id.url,
                self.external_id
            )
        elif self.external_source_id.type == 'woocommerce':
            self.external_url = '%swp-admin/post.php?post=%s&action=edit' % (
                self.external_source_id.url,
                self.external_id
            )
    # fields
    woocommerce_state = fields.Selection(
        [
            ('none', 'None'),
            ('pending', 'Pending Payment'),
            ('shipped', 'Shipped'),
            ('processing', 'Processing'),
            ('on-hold', 'On Hold'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
            ('refunded', 'Refunded'),
            ('failed', 'Failed')
        ],
        string='Woocommerce State',
        default='none'
    )
    external_id = fields.Char(
        string='External Id'
    )
    external_customer_id = fields.Many2one(
        comodel_name='external.customer',
        string='Customer'
    )
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='Source'
    )
    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Albaran'
    )
    number = fields.Integer(
        string='Number'
    )
    external_source_name = fields.Selection(
        [
            ('web', 'Web')
        ],
        string='External Source Name',
        default='web'
    )
    external_stock_picking_line_ids = fields.One2many(
        'external.stock.picking.line',
        'external_stock_picking_id',
        string='Lines',
        copy=True
    )

    @api.multi
    def action_run_multi(self):
        for item in self:
            if item.picking_id.id == 0:
                item.action_run()

    @api.multi
    def allow_create(self):
        return_item = False
        # operations
        for item in self:
            if item.external_source_id:
                # woocommerce
                if item.external_source_id.type == 'woocommerce':
                    if item.woocommerce_state in ['processing', 'shipped', 'completed']:
                        return_item = True
                elif item.external_source_id.type == 'custom':
                    return_item = True
        # return
        return return_item

    @api.multi
    def action_run(self):
        for item in self:
            # allow_create
            allow_create_item = item.allow_create()[0]
            if allow_create_item:
                item.action_stock_picking_create()

    @api.multi
    def action_stock_picking_create(self):
        for item in self:
            if item.picking_id.id == 0:
                # allow_create
                allow_create_stock_picking = False
                if item.external_customer_id:
                    if item.external_customer_id.partner_id:
                        allow_create_stock_picking = True
                        # check_external_stock_picking_line_ids
                        for line_id in item.external_stock_picking_line_ids:
                            if line_id.external_product_id.id == 0:
                                allow_create_stock_picking = False
                # operations
                if allow_create_stock_picking:
                    # define
                    item_es = item.external_source_id
                    item_es_espt = \
                        item_es.external_stock_picking_picking_type_id
                    item_es_espc = item_es.external_stock_picking_carrier_id
                    # stock_picking
                    vals = {
                        'external_stock_picking_id': item.id,
                        'picking_type_id': item_es_espt.id,
                        'location_id':
                            item_es_espt.default_location_src_id.id,
                        'location_dest_id': 9,
                        'move_type' : 'one',
                        'partner_id': item.external_customer_id.partner_id.id,
                        'move_lines': []
                    }
                    # carrier_id
                    if item_es_espc:
                        vals['carrier_id'] = item_es_espc.id
                    # move_lines
                    for line_id in item.external_stock_picking_line_ids:
                        line_id_ep = line_id.external_product_id
                        if line_id_ep:
                            line_id_ep_pt = line_id_ep.product_template_id
                            # vals
                            line_vals = {
                                'product_id':line_id_ep_pt.id,
                                'name': line_id_ep_pt.name,
                                'product_uom_qty': line_id.quantity,
                                'product_uom': line_id_ep_pt.uom_id.id,
                                'state': 'draft'
                            }
                            vals['move_lines'].append((0, 0, line_vals))
                    # create
                    obj = self.env['stock.picking'].create(vals)
                    # update
                    item.picking_id = obj.id
                    # lines
                    for move_line in item.picking_id.move_lines:
                        items = self.env[
                            'external.stock.picking.line'
                        ].sudo().search(
                            [
                                ('external_stock_picking_id', '=', item.id),
                                ('external_product_id.product_template_id', '=',
                                 move_line.product_id.id)
                            ]
                        )
                        if items:
                            items[0].move_id = move_line.id
                    # action_confirm
                    item.picking_id.action_confirm()
                    # force_assign
                    item.picking_id.force_assign()
        # return
        return False
