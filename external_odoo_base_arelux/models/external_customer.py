# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools

import logging
_logger = logging.getLogger(__name__)

import requests, json
from dateutil.relativedelta import relativedelta
from datetime import datetime
import pytz

class ExternalCustomer(models.Model):
    _inherit = 'external.customer'                     
    
    @api.one
    def operations_item(self):
        return_item = super(ExternalCustomer, self).operations_item()        
        #partner_id        
        if self.partner_id.id>0:
            if self.external_source_id.id>0:
                #ar_qt_activity_type
                self.partner_id.ar_qt_activity_type = self.external_source_id.external_customer_ar_qt_activity_type
                #ar_qt_customer_type
                self.partner_id.ar_qt_customer_type = self.external_source_id.external_customer_ar_qt_customer_type
                #external_customer_res_partner_category_id
                if self.external_source_id.external_customer_res_partner_category_id.id>0:
                    self.partner_id.category_id = [(4, self.external_source_id.external_customer_res_partner_category_id.id)]
                #external_customer_res_partner_contact_form
                if self.external_source_id.external_customer_res_partner_contact_form.id>0:
                    if self.partner_id.ar_qt_activity_type=='arelux':
                        self.partner_id.ar_qt_arelux_contact_form = [(4, self.external_source_id.external_customer_res_partner_contact_form.id)]
                    elif self.partner_id.ar_qt_activity_type=='todocesped':
                        self.partner_id.ar_qt_todocesped_contact_form = [(4, self.external_source_id.external_customer_res_partner_contact_form.id)]                
        #return
        return return_item    