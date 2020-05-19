# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)

from odoo import api, models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    external_sale_order_id = fields.Many2one(
        comodel_name='external.sale.order',
        string='External Sale Order Id'
    )