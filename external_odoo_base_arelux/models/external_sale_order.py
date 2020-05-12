# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

class ExternalSaleOrder(models.Model):
    _inherit = 'external.sale.order'             
        
    @api.one
    def action_crm_lead_create(self):
        return_item = super(ExternalSaleOrder, self).action_crm_lead_create()        
        #lead_id
        if self.lead_id.id>0:
            #external_customer_id
            if self.external_customer_id.id>0 and self.external_customer_id.partner_id.id>0:
                self.lead_id.ar_qt_activity_type = self.external_customer_id.partner_id.ar_qt_activity_type
                self.lead_id.ar_qt_customer_type = self.external_customer_id.partner_id.ar_qt_customer_type
            else:                   
                self.lead_id.ar_qt_activity_type = 'arelux'
                self.lead_id.ar_qt_customer_type = 'particular'             
        #return
        return return_item
    
    @api.one
    def action_sale_order_done_error_external_shipping_address_id_without_country_id(self):
        _logger.info('No se puede confirmar el pedido '+str(self.sale_order_id.name)+' porque la direccion de envio del cliente NO tiene PAIS mapeado')
        
    @api.one
    def action_sale_order_done_error_external_shipping_address_id_without_country_state_id(self):
        _logger.info('No se puede confirmar el pedido '+str(self.sale_order_id.name)+' porque la direccion de envio del cliente NO tiene PROVINCIA mapeada')        
    
    @api.one
    def action_sale_order_done(self):
        #antes
        if self.sale_order_id.id>0:
            if self.sale_order_id.state in ['draft', 'sent']:
                weight_total = 0
                for order_line_item in self.sale_order_id.order_line:
                    if order_line_item.product_id.id>0:
                        if order_line_item.product_uom_qty>0:
                            if order_line_item.product_id.weight>0:
                                weight_item = order_line_item.product_id.weight*order_line_item.product_uom_qty
                                weight_total += weight_item
                #operations
                if self.external_source_id.id>0:
                    if self.external_source_id.external_sale_order_carrier_id.id>0:
                        if weight_total<=10:
                            self.sale_order_id.carrier_id = self.external_source_id.external_sale_order_carrier_id.id
        #check country_id and state_id
        allow_confirm = True
        if self.external_shipping_address_id.id>0:
            #check_country_id
            if self.external_shipping_address_id.country_id.id==0:
                self.action_sale_order_done_error_external_shipping_address_id_without_country_id()
                allow_confirm = False
            if self.external_shipping_address_id.country_state_id.id==0:
                self.action_sale_order_done_error_external_shipping_address_id_without_country_state_id()
                allow_confirm = False                
        #allow_confirm
        if allow_confirm==True:
            return super(ExternalSaleOrder, self).action_sale_order_done()            