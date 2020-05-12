# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

class ExternalStockPicking(models.Model):
    _inherit = 'external.stock.picking'
    
    @api.one
    def action_run(self):
        return_item = super(ExternalStockPicking, self).action_run()        
        #picking
        if self.picking_id.id>0:
            #external_customer_id > partner_id info
            if self.external_customer_id.id>0:
                if self.external_customer_id.partner_id.id>0:
                    self.picking_id.ar_qt_activity_type = self.external_customer_id.partner_id.ar_qt_activity_type
                    self.picking_id.ar_qt_customer_type = self.external_customer_id.partner_id.ar_qt_customer_type
            #carrier_id (nacex only if 10kg)
            if self.picking_id.weight<=10: 
                delivery_carrier_ids = self.env['delivery.carrier'].sudo().search([('carrier_type', '=', 'nacex')])
                if len(delivery_carrier_ids)>0:
                    delivery_carrier_id = delivery_carrier_ids[0]
                    self.picking_id.carrier_id = delivery_carrier_id.id#Nacex 
        #return
        return return_item