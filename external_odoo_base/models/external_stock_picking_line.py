# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

import boto3
from botocore.exceptions import ClientError

class ExternalStockPickingLine(models.Model):
    _name = 'external.stock.picking.line'
    _description = 'External Stock Picking Line'
    _order = 'create_date desc'
    
    line_id = fields.Char(
        string='Line Id'
    )
    external_id = fields.Char(
        string='External Id (Product id)'
    )
    external_variant_id = fields.Char(
        string='External Variant Id'
    )
    external_product_id = fields.Many2one(
        comodel_name='external.product',
        string='External Product'
    )
    external_stock_picking_id = fields.Many2one(
        comodel_name='external.stock.picking',
        string='External Sale Order',
        ondelete='cascade'
    )    
    title = fields.Char(
        string='Title'
    )
    quantity = fields.Integer(
        string='Quantity'
    )    
    move_id = fields.Many2one(
        comodel_name='stock.move',
        string='Stock Move'
    )
    invoice_line_id = fields.Many2one(
        comodel_name='account.invoice.line',
        string='Account Invoice Line'
    )        

    @api.one
    def operations_item(self):
        if self.external_product_id.id==0:
            if self.external_stock_picking_id.id>0:
                external_product_ids = self.env['external.product'].sudo().search(
                    [
                        ('source', '=', str(self.external_stock_picking_id.source)),
                        ('external_id', '=', str(self.external_id)),
                        ('external_variant_id', '=', str(self.external_variant_id))
                    ]
                )
                if len(external_product_ids)>0:
                    external_product_id = external_product_ids[0]
                    self.external_product_id = external_product_id.id
        #return
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalStockPickingLine, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item
        
    @api.multi
    def cron_external_stock_picking_line_generate_invoice_lines(self, cr=None, uid=False, context=None):
        _logger.info('cron_external_stock_picking_line_generate_invoice_lines')
        #params
        external_odoo_journal_id = int(self.env['ir.config_parameter'].sudo().get_param('external_odoo_journal_id'))
        #search
        external_stock_picking_line_ids = self.env['external.stock.picking.line'].sudo().search(
            [
                ('invoice_line_id', '=', False),
                ('external_stock_picking_id.picking_id', '!=', False),
                ('external_stock_picking_id.picking_id.state', '=', 'done'),
                ('external_product_id', '!=', False),
                ('external_product_id.invoice_partner_id', '!=', False)
            ]
        )
        if len(external_stock_picking_line_ids)>0:
            for external_stock_picking_line_id in external_stock_picking_line_ids:
                external_stock_picking_line_ids_by_partner_ids = {}
                if external_stock_picking_line_id.external_product_id.invoice_partner_id.id not in external_stock_picking_line_ids_by_partner_ids:
                    external_stock_picking_line_ids_by_partner_ids[external_stock_picking_line_id.external_product_id.invoice_partner_id.id] = []
                #append
                external_stock_picking_line_ids_by_partner_ids[external_stock_picking_line_id.external_product_id.invoice_partner_id.id].append(external_stock_picking_line_id)
            #external_stock_picking_line_ids_by_partner_ids
            for external_stock_picking_line_ids_by_partner_id in external_stock_picking_line_ids_by_partner_ids:
                #operations
                partner_id = external_stock_picking_line_ids_by_partner_id
                res_partner_id = self.env['res.partner'].sudo().browse(partner_id)
                external_stock_picking_line_ids = external_stock_picking_line_ids_by_partner_ids[external_stock_picking_line_ids_by_partner_id]
                #search draft invoice
                account_invoice_ids = self.env['account.invoice'].sudo().search(
                    [
                        ('partner_id', '=', res_partner_id.id),
                        ('state', '=', 'draft'),
                        ('type', '=', 'out_invoice'),
                        ('journal_id', '=', external_odoo_journal_id)
                    ]
                )
                if len(account_invoice_ids)>0:
                    account_invoice_id = account_invoice_ids[0]
                else:
                    #create_proccess
                    account_invoice_vals = {
                        'partner_id': res_partner_id.id,
                        'partner_shipping_id': res_partner_id.id,
                        'state': 'draft',
                        'type': 'out_invoice',
                        'journal_id': external_odoo_journal_id,
                        'user_id': 0, 
                    }
                    #property_payment_term_id
                    if res_partner_id.property_payment_term_id.id>=0:
                        account_invoice_vals['payment_term_id'] = res_partner_id.property_payment_term_id.id
                    #customer_payment_mode_id
                    if res_partner_id.customer_payment_mode_id.id>0:
                        account_invoice_vals['payment_mode_id'] = res_partner_id.customer_payment_mode_id.id 
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