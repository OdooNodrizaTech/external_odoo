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
from woocommerce import API

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