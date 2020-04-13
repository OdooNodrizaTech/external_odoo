# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'                     
    
    @api.multi
    def action_invoice_open(self):
        #operations
        for obj in self:
            if obj.type=='out_invoice':
                order_ids = []
                for invoice_line_id in obj.invoice_line_ids:
                    sale_order_line_invoice_rel_ids = self.env['sale.order.line'].sudo().search([('invoice_lines', 'in', invoice_line_id.id)])
                    if len(sale_order_line_invoice_rel_ids)>0:
                        for sale_order_line_invoice_rel_id in sale_order_line_invoice_rel_ids:
                            if sale_order_line_invoice_rel_id.order_id.id not in order_ids:
                                order_ids.append(int(sale_order_line_invoice_rel_id.order_id.id))
                #check
                if len(order_ids)>0:
                    external_sale_order_ids = self.env['external.sale.order'].sudo().search([('sale_order_id', 'in', order_ids)])
                    if len(external_sale_order_ids)>0:
                        amount_total_sale_orders = 0
                        for external_sale_order_id in external_sale_order_ids:
                            amount_total_sale_orders += external_sale_order_id.sale_order_id.amount_total
                        #difference
                        difference = amount_total_sale_orders-obj.amount_total
                        if difference!=0:      
                            if difference>0:
                                obj.tax_line_ids[0].amount = obj.tax_line_ids[0].amount-difference
                            else:
                                obj.tax_line_ids[0].amount = obj.tax_line_ids[0].amount+difference
        #action
        return super(AccountInvoice, self).action_invoice_open()            