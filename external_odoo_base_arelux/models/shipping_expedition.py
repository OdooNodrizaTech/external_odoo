from odoo import api, models, fields

import logging
_logger = logging.getLogger(__name__)

class ShippingExpedition(models.Model):
    _inherit = 'shipping.expedition'

    @api.model
    def create(self, values):
        return_object = super(ShippingExpedition, self).create(values)
        #operations
        if return_object.user_id.id==0:
            if return_object.picking_id.id>0:
                if return_object.picking_id.external_stock_picking_id.id>0:
                    if external_stock_picking_id.external_stock_picking_id.external_source_id.id>0:
                        if external_stock_picking_id.external_stock_picking_id.external_source_id.external_stock_picking_user_id.id>0:
                            return_object.user_id = external_stock_picking_id.external_stock_picking_id.external_source_id.external_stock_picking_user_id.id
        #return
        return return_object