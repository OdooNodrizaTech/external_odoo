# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalCustomer(models.Model):
    _name = 'external.customer'
    _description = 'External Customer'
    _order = 'create_date desc'

    name = fields.Char(        
        compute='_get_name',
        string='Nombre',
        store=False
    )
    
    @api.one        
    def _get_name(self):            
        for obj in self:
            obj.name = obj.first_name
            #Fix
            if obj.last_name!=False:
                obj.name += ' '+str(self.last_name)
    #fields
    external_id = fields.Char(
        string='External Id'
    )
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='Source'
    )            
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner'
    )
    vat = fields.Char(
        string='Vat'
    )
    email = fields.Char(
        string='Email'
    )
    accepts_marketing = fields.Boolean(
        string='Accepts Marketing'
    )
    first_name = fields.Char(
        string='First Name'
    )
    last_name = fields.Char(
        string='Last Name'
    )
    company = fields.Char(
        string='Company'
    )
    address_1 = fields.Char(
        string='Address 1'
    )
    address_2 = fields.Char(
        string='Address 2'
    )
    city = fields.Char(
        string='City'
    )       
    active = fields.Boolean(
        string='Active'
    )
    phone = fields.Char(
        string='Phone'
    )
    country_code = fields.Char(
        string='Country Code'
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country'
    )
    province_code = fields.Char(
        string='Province Code'
    )
    postcode = fields.Char(
        string='Postcode'
    )    
    country_state_id = fields.Many2one(
        comodel_name='res.country.state',
        string='Country State'
    )
    
    @api.multi
    def action_operations_item(self):
        for obj in self:
            if obj.partner_id.id==0:
                obj.action_operations_item()  

    @api.one
    def operations_item(self):
        if self.partner_id.id==0:
            #phone
            phone = None
            mobile = None
            ##phone_mobile
            if self.phone!=False:
                #phone vs mobile
                phone = str(self.phone)
                mobile = None
                phone_first_char = str(self.phone)[:1]
                if phone_first_char=='6':
                    mobile = str(phone)
                    phone = None
                #search
                if phone!=None:
                    res_partner_ids = self.env['res.partner'].sudo().search(
                        [
                            ('type', '=', 'contact'),
                            ('email', '=', str(self.email)),
                            ('active', '=', True),
                            ('supplier', '=', False),
                            ('phone', '=', str(phone))
                        ]
                    )
                else:
                    res_partner_ids = self.env['res.partner'].sudo().search(
                        [
                            ('type', '=', 'contact'),
                            ('email', '=', str(self.email)),
                            ('active', '=', True),
                            ('supplier', '=', False),
                            ('mobile', '=', str(mobile))
                        ]
                    )
            else:
                res_partner_ids = self.env['res.partner'].sudo().search([('email', '=', str(self.email)),('active', '=', True),('supplier', '=', False)])
            #if exists
            if len(res_partner_ids)>0:
                res_partner_id = res_partner_ids[0]
                self.partner_id = res_partner_id.id
                #Update country_id
                if self.partner_id.country_id.id>0:
                    self.country_id = self.partner_id.country_id.id
                #Update state_id
                if self.partner_id.state_id.id>0:
                    self.country_state_id = self.partner_id.state_id.id
            else:
                #create
                res_partner_vals = {
                    'active': True,
                    'customer': True,
                    'supplier': False,
                    'name': str(self.first_name)+' '+str(self.last_name),
                    'email': str(self.email),
                    'street': str(self.address_1),
                    'street2': str(self.address_2),
                    'city': str(self.city),
                    'zip': str(self.postcode)
                }
                #phone_mobile
                if phone!=None:
                    res_partner_vals['phone'] = str(phone)
                else:
                    res_partner_vals['mobile'] = str(mobile)
                #vat
                if self.vat!=False:
                    res_partner_vals['vat'] = 'EU'+str(self.vat)                    
                #country_id
                if self.country_code!=False:
                    res_country_ids = self.env['res.country'].sudo().search([('code', '=', str(self.country_code))])
                    if len(res_country_ids)>0:
                        res_country_id = res_country_ids[0]
                        res_partner_vals['country_id'] = res_country_id.id
                        #state_id
                        if self.province_code!=False:
                            res_country_state_ids = self.env['res.country.state'].sudo().search([('country_id', '=', res_country_id.id),('code', '=', str(self.province_code))])
                            if len(res_country_state_ids)>0:
                                res_country_state_id = res_country_state_ids[0]
                                res_partner_vals['state_id'] = res_country_state_id.id
                #create
                res_partner_obj = self.env['res.partner'].create(res_partner_vals)
                self.partner_id = res_partner_obj.id                        
        #return
        return False        

    @api.model
    def create(self, values):
        return_item = super(ExternalCustomer, self).create(values)        
        # operations
        return_item.operations_item()
        # return
        return return_item    