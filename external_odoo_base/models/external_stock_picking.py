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
        self.ensure_one()
        if self.picking_id.id == 0:
            self.action_run()

    @api.multi
    def allow_create(self):
        self.ensure_one()
        return_item = False
        # operations
        if self.external_source_id:
            # woocommerce
            if self.external_source_id.type == 'woocommerce':
                if self.woocommerce_state in ['processing', 'shipped', 'completed']:
                    return_item = True
            elif self.external_source_id.type == 'custom':
                return_item = True
        # return
        return return_item
        
    @api.multi
    def action_run(self):
        self.ensure_one()
        # allow_create
        allow_create_item = self.allow_create()[0]
        if allow_create_item:
            self.action_stock_picking_create()
        
    @api.multi
    def action_stock_picking_create(self):
        self.ensure_one()
        if self.picking_id.id == 0:
            # allow_create
            allow_create_stock_picking = False
            if self.external_customer_id:
                if self.external_customer_id.partner_id:
                    allow_create_stock_picking = True
                    # check_external_stock_picking_line_ids
                    for external_stock_picking_line_id in self.external_stock_picking_line_ids:
                        if external_stock_picking_line_id.external_product_id.id == 0:
                            allow_create_stock_picking = False
            # operations
            if allow_create_stock_picking:
                # stock_picking
                vals = {
                    'external_stock_picking_id': self.id,
                    'picking_type_id' :
                        self.external_source_id.external_stock_picking_picking_type_id.id,
                    'location_id':
                        self.external_source_id.external_stock_picking_picking_type_id.default_location_src_id.id,
                    'location_dest_id': 9,
                    'move_type' : 'one',
                    'partner_id': self.external_customer_id.partner_id.id,
                    'move_lines': []             
                }
                # carrier_id
                if self.external_source_id.external_stock_picking_carrier_id:
                    vals['carrier_id'] = \
                        self.external_source_id.external_stock_picking_carrier_id.id
                # move_lines
                for external_stock_picking_line_id in self.external_stock_picking_line_ids:
                    if external_stock_picking_line_id.external_product_id:
                        line_vals = {
                            'product_id':
                                external_stock_picking_line_id.external_product_id.product_template_id.id,
                            'name':
                                external_stock_picking_line_id.external_product_id.product_template_id.name,
                            'product_uom_qty': external_stock_picking_line_id.quantity,
                            'product_uom':
                                external_stock_picking_line_id.external_product_id.product_template_id.uom_id.id,
                            'state': 'draft',                        
                        }
                        vals['move_lines'].append((0, 0, line_vals))
                # create
                obj = self.env['stock.picking'].create(vals)
                # update
                self.picking_id = obj.id
                # lines
                for move_line in self.picking_id.move_lines:
                    items = self.env['external.stock.picking.line'].sudo().search(
                        [
                            ('external_stock_picking_id', '=', self.id),
                            ('external_product_id.product_template_id', '=', move_line.product_id.id)
                        ]
                    )
                    if items:
                        items[0].move_id = move_line.id
                # action_confirm
                self.picking_id.action_confirm()
                # force_assign
                self.picking_id.force_assign()
        # return
        return False
