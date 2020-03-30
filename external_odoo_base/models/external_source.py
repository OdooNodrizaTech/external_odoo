# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz
from odoo.exceptions import Warning

class ExternalSource(models.Model):
    _name = 'external.source'
    _description = 'External Source'

    name = fields.Char(
        string='Name'
    )                        
    type = fields.Selection(
        [
            ('custom', 'Custom'),
            ('shopify', 'Shopify'),
            ('woocommerce', 'Woocommerce'),
        ],
        string='Type',
        default='custom'
    )
    url = fields.Char(
        string='Url'
    )
    external_sale_order_user_id = fields.Many2one(
        comodel_name='res.users',
        string='User id',
        help='User id (external.sale.order)',
    )
    external_sale_order_account_payment_mode_id = fields.Many2one(
        comodel_name='account.payment.mode',
        string='Payment mode id',
        help='Payment mode id (external.sale.order)'
    )
    external_sale_order_account_payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string='Payment term id',
        help='Payment term id (external.sale.order)'
    )
    external_sale_order_shipping_product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template id',
        help='Product Template id (external.sale.order.shipping)',
    )
    external_stock_picking_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Stock Picking Type Id',
        help='Stock Picking Type Id (external.stock.picking)',
    )
    external_stock_picking_carrier_id = fields.Many2one(
        comodel_name='delivery.carrier',
        string='Delivery Carrier Id',
        help='Delivery Carrier Id (external.stock.picking)'
    )
    invoice_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner Id',
        help='Partner id (Auto-invoice in stock.picking)'
    )
    invoice_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal Id',
        help='Journal id (Auto-invoice in stock.picking)'
    )
    api_status = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('valid', 'Valida')
        ],
        string='Api Status',
        default='draft'
    )
    api_key = fields.Char(
        string='Api Key'
    )
    api_secret = fields.Char(
        string='Api Secret'
    )
        
    @api.multi
    def action_api_status_draft_multi(self):
        for obj in self:
            if obj.api_status=='valid':
                obj.action_api_status_draft()
                
    @api.one
    def action_api_status_draft(self):
        self.api_status = 'draft'                        
    
    @api.multi
    def action_api_status_valid_multi(self):
        for obj in self:
            if obj.api_status=='draft':
                if obj.url!=False and obj.api_key!=False and obj.api_secret!=False:
                    return_item = obj.action_api_status_valid()
                    if return_item==False:
                        raise Warning("No se ha podido validar la integracion con la API (quizas no esta disponible todavia)")
                    else:
                        obj.api_status = 'valid'
                else:
                    raise Warning("Los campos de api_key y api_secret son necesarios")                        
                    
                    
    @api.one
    def action_api_status_valid(self):
        return super(ExternalSource, self).action_api_status_valid()                    
        
    @api.multi
    def action_operations_get_products_multi(self):
        for obj in self:
            if obj.api_key!=False and obj.api_secret!=False:
                obj.action_operations_get_products()                
        
    @api.one
    def action_operations_get_products(self):
        return False
        
    @api.multi
    def cron_external_stock_picking_line_generate_invoice_lines(self, cr=None, uid=False, context=None):
        _logger.info('cron_external_stock_picking_line_generate_invoice_lines')
        #source
        external_source_ids = self.env['external.source'].sudo().search(
            [
                ('type', '=', 'woocommerce'),
                ('invoice_partner_id', '!=', False),
                ('invoice_journal_id', '!=', False)                
            ]
        )
        if len(external_source_ids)>0:
            for external_source_id in external_source_ids:
                #external_stock_picking_line_ids
                external_stock_picking_line_ids = self.env['external.stock.picking.line'].sudo().search(
                    [
                        ('external_source_id', '=', external_source_ids.id),
                        ('invoice_line_id', '=', False),
                        ('external_stock_picking_id.picking_id', '!=', False),
                        ('external_stock_picking_id.picking_id.state', '=', 'done'),
                        ('external_product_id', '!=', False),
                        ('external_product_id.invoice_partner_id', '!=', False)
                    ]
                )
                if len(external_stock_picking_line_ids)>0:
                    #search draft invoice
                    account_invoice_ids = self.env['account.invoice'].sudo().search(
                        [
                            ('partner_id', '=', external_source_id.invoice_partner_id.id),
                            ('state', '=', 'draft'),
                            ('type', '=', 'out_invoice'),
                            ('journal_id', '=', external_source_id.invoice_journal_id.id)
                        ]
                    )
                    if len(account_invoice_ids)>0:
                        account_invoice_id = account_invoice_ids[0]
                    else:
                        #create_proccess
                        account_invoice_vals = {
                            'partner_id': external_source_id.invoice_partner_id.id,
                            'partner_shipping_id': external_source_id.invoice_partner_id.id,
                            'state': 'draft',
                            'type': 'out_invoice',
                            'journal_id': external_source_id.invoice_journal_id.id,
                            'user_id': 0, 
                        }
                        #property_payment_term_id
                        if external_source_id.invoice_partner_id.property_payment_term_id.id>=0:
                            account_invoice_vals['payment_term_id'] = external_source_id.invoice_partner_id.property_payment_term_id.id
                        #customer_payment_mode_id
                        if external_source_id.invoice_partner_id.customer_payment_mode_id.id>0:
                            account_invoice_vals['payment_mode_id'] = external_source_id.invoice_partner_id.customer_payment_mode_id.id 
                        #create
                        account_invoice_obj = self.env['account.invoice'].create(account_invoice_vals)
                        account_invoice_id = account_invoice_obj
                    #add_lines
                    for external_stock_picking_line_id in external_stock_picking_line_ids:
                        #vals
                        account_invoice_line_vals = {
                            'invoice_id': account_invoice_id.id,
                            'product_id': external_stock_picking_line_id.external_product_id.product_template_id.id,
                            'name': str(external_stock_picking_line_id.title) + ' ('+str(external_stock_picking_line_id.external_stock_picking_id.picking_id.name)+')',
                            'quantity': external_stock_picking_line_id.quantity,
                            'price_unit': external_stock_picking_line_id.external_product_id.product_template_id.list_price,                        
                            'currency_id': account_invoice_id.currency_id.id,                        
                        }
                        #account_id
                        if external_stock_picking_line_id.external_product_id.product_template_id.property_account_income_id.id>0:
                            account_invoice_line_vals['account_id'] = external_stock_picking_line_id.external_product_id.product_template_id.property_account_income_id.id
                        else:
                            account_invoice_line_vals['account_id'] = external_stock_picking_line_id.external_product_id.product_template_id.categ_id.property_account_income_categ_id.id
                        #create
                        account_invoice_line_obj = self.env['account.invoice.line'].create(account_invoice_line_vals)
                        #onchange
                        account_invoice_line_obj._onchange_product_id()
                        account_invoice_line_obj._onchange_account_id()
                        account_invoice_line_obj.name = str(external_stock_picking_line_id.title) + ' ('+str(external_stock_picking_line_id.external_stock_picking_id.picking_id.name)+')'
                        #update
                        external_stock_picking_line_id.invoice_line_id = account_invoice_line_obj.id                                                    