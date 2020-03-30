# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalProduct(models.Model):
    _name = 'external.product'
    _description = 'External Product'
    _order = 'create_date desc'

    external_id = fields.Char(
        string='External Id'
    )    
    external_variant_id = fields.Char(
        string='External Variant Id'
    )
    name = fields.Char(
        string='Name'
    )
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='External Source'
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