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
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='Source'
    )                
    product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template'
    )        

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