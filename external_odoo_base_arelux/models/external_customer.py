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

class ExternalCustomer(models.Model):
    _inherit = 'external.customer'                     
    
    @api.one
    def operations_item(self):
        return_item = super(ExternalCustomer, self).operations_item()        
        #partner_id
        if self.partner_id.id>0:
            #ar_qt
            self.partner_id.ar_qt_activity_type = 'arelux'
            self.partner_id.ar_qt_customer_type = 'particular'
            #update category_id=53 (Orache)
            if self.external_source_id.id>0:
                if 'www.orache.shop' in self.external_source_id.url:
                    self.partner_id.category_id = [(4, 53)]
        #return
        return return_item    