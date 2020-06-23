# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

class ExternalProduct(models.Model):
    _name = 'external.product'
    _description = 'External Product'
    _order = 'create_date desc'
    
    name = fields.Char(        
        compute='_get_name',
        string='Nombre',
        store=False
    )
    
    @api.one        
    def _get_name(self):            
        for obj in self:
            obj.name = obj.external_id
    #fields
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
        compute='_get_external_url',
        string='External Url',
        store=False
    )

    @api.one
    def _get_external_url(self):
        for obj in self:
            if obj.external_source_id.id > 0:
                if obj.external_id != False:
                    obj.external_url = ''
                    if obj.external_source_id.type == 'shopify':
                        obj.external_url = 'https://' + str(obj.external_source_id.url) + '/admin/products/' + str(obj.external_id)
                    elif obj.external_source_id.type == 'woocommerce':
                        obj.external_url = str(obj.external_source_id.url) + 'wp-admin/post.php?post=' + str(obj.external_id) + '&action=edit'

    @api.one
    def operations_item(self):
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalProduct, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item    