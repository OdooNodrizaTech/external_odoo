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

class ExternalAddress(models.Model):
    _name = 'external.address'
    _description = 'External Address'
    _order = 'create_date desc'

    external_id = fields.Char(
        string='External Id'
    )
    external_customer_id = fields.Many2one(
        comodel_name='external.customer',
        string='External Customer'
    )
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='External Source'
    )                        
    type = fields.Selection(
        [
            ('invoice', 'Invoice'),
            ('delivery', 'Delivery')
        ],
        string='Type',
        default='invoice'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner'
    )
    first_name = fields.Char(
        string='First Name'
    )
    address1 = fields.Char(
        string='Address1'
    )
    phone = fields.Char(
        string='Phone'
    )
    city = fields.Char(
        string='City'
    )
    last_name = fields.Char(
        string='Last Name'
    )    
    address2 = fields.Char(
        string='Address2'
    )
    company = fields.Char(
        string='Company'
    )
    latitude = fields.Char(
        string='Latitude'
    )
    longitude = fields.Char(
        string='Longitude'
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
    country_state_id = fields.Many2one(
        comodel_name='res.country.state',
        string='Country State'
    )
    postcode = fields.Char(
        string='Postcode'
    )   

    @api.one
    def operations_item(self):
        if self.partner_id.id==0:
            #phone_mobile
            phone = str(self.phone)
            mobile = None
            phone_first_char = str(self.phone)[:1]
            if phone_first_char=='6':
                mobile = str(phone)
                phone = None
            #external_customer_id
            if self.external_customer_id.id>0:
                if self.external_customer_id.partner_id.id>0:
                    #name
                    name = str(self.first_name)
                    #fix_last_name
                    if self.last_name!=False:
                        name += ' '+str(self.last_name)
                    #search
                    res_partner_ids = self.env['res.partner'].sudo().search(
                        [
                            ('parent_id', '=', self.external_customer_id.partner_id.id),
                            ('type', '=', str(self.type)),
                            ('name', '=', str(name))
                        ]
                    )
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
                            'type': str(self.type),
                            'parent_id': self.external_customer_id.partner_id.id,
                            'active': True,
                            'customer': True,
                            'supplier': False,
                            'name': str(name),
                            'email': str(self.external_customer_id.partner_id.email),
                            'city': str(self.city)
                        }
                        #street
                        if self.address1!=False:
                            res_partner_vals['street'] = str(self.address1) 
                        #stree2
                        if self.address2!=False:
                            res_partner_vals['stree2'] = str(self.address2)
                        #zip
                        if self.postcode!=False:
                            res_partner_vals['zip'] = str(self.postcode)
                        #phone_mobile
                        if phone!=None:
                            res_partner_vals['phone'] = str(phone)
                        else:
                            res_partner_vals['mobile'] = str(mobile)
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
        return_item = super(ExternalAddress, self).create(values)
        # operations
        return_item.operations_item()
        # return
        return return_item    