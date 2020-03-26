# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalStockPicking(models.Model):
    _inherit = 'external.stock.picking'
    
    @api.one
    def action_run(self):
        return_item = super(ExternalStockPicking, self).action_run()        
        #picking
        if self.picking_id.id>0:
            #ar_qt
            self.picking_id.ar_qt_activity_type = 'arelux'
            self.picking_id.ar_qt_customer_type = 'particular'
            #carrier_id (nacex only if 1kg)
            if self.external_source_id.id>0:
                if 'www.orache.shop' in self.external_source_id.url:
                    if self.picking_id.weight<=1: 
                        delivery_carrier_ids = self.env['delivery.carrier'].sudo().search([('carrier_type', '=', 'nacex')])
                        if len(delivery_carrier_ids)>0:
                            delivery_carrier_id = delivery_carrier_ids[0]
                            self.picking_id.carrier_id = delivery_carrier_id.id#Nacex 
        #return
        return return_item