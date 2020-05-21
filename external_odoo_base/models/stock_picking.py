# -*- coding: utf-8 -*-
from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    external_stock_picking_id = fields.Many2one(
        comodel_name='external.stock.picking',
        string='External Stock Picking Id'
    )