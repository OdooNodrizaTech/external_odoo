# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ExternalAddress(models.Model):
    _name = 'external.address'
    _description = 'External Address'
    _order = 'create_date desc'

    name = fields.Char(
        compute='_compute_name',
        string='Name',
        store=False
    )

    @api.multi
    def _compute_name(self):
        self.ensure_one()
        self.name = self.first_name
        if self.last_name:
            self.name = "%s %s" % (
                self.first_name,
                self.last_name
            )
    # fields
    external_id = fields.Char(
        string='External Id'
    )
    external_customer_id = fields.Many2one(
        comodel_name='external.customer',
        string='Customer'
    )
    external_source_id = fields.Many2one(
        comodel_name='external.source',
        string='Source'
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

    @api.multi
    def operations_item(self):
        self.ensure_one()
        if self.partner_id:
            # define
            phone = None
            mobile = None
            # phone_mobile
            if self.phone:
                phone = str(self.phone)
                phone_first_char = str(self.phone)[:1]
                if phone_first_char == '6':
                    mobile = str(phone)
                    phone = None
            # external_customer_id
            if self.external_customer_id:
                if self.external_customer_id.partner_id:
                    # name
                    name = str(self.first_name)
                    # fix_last_name
                    if self.last_name:
                        name = "%s %s" % (
                            self.first_name,
                            self.last_name
                        )
                    # create
                    vals = {
                        'type': str(self.type),
                        'parent_id': self.external_customer_id.partner_id.id,
                        'active': True,
                        'customer': True,
                        'supplier': False,
                        'name': str(name),
                        'city': str(self.city)
                    }
                    # email
                    if self.external_customer_id.partner_id.email:
                        vals['email'] = str(self.external_customer_id.partner_id.email)
                    # street
                    if self.address1:
                        vals['street'] = str(self.address1)
                    # street2
                    if self.address2:
                        vals['street2'] = str(self.address2)
                    # zip
                    if self.postcode:
                        vals['zip'] = str(self.postcode)
                    # phone_mobile
                    if phone is not None:
                        vals['phone'] = str(phone)
                    else:
                        vals['mobile'] = str(mobile)
                    # country_id
                    if self.country_code:
                        items = self.env['res.country'].sudo().search(
                            [
                                ('code', '=', str(self.country_code))
                            ]
                        )
                        if items:
                            # update_country_id
                            self.country_id = items[0].id
                            vals['country_id'] = items[0].id
                            # state_id
                            if self.province_code:
                                items = self.env['res.country.state'].sudo().search(
                                    [
                                        ('country_id', '=', self.country_id.id),
                                        ('code', '=', str(self.province_code))
                                    ]
                                )
                                if items:
                                    # update_state_id
                                    self.country_state_id = items[0].id
                                    vals['state_id'] = items[0].id
                                else:
                                    if self.postcode:
                                        items = self.env['res.better.zip'].sudo().search(
                                            [
                                                ('country_id', '=', self.country_id.id),
                                                ('name', '=', str(self.postcode))
                                            ]
                                        )
                                        if items:
                                            if items[0].state_id:
                                                # update_state_id
                                                self.country_state_id = items[0].state_id.id
                                                vals['state_id'] = items[0].state_id.id
                    # create
                    res_partner_obj = self.env['res.partner'].create(vals)
                    self.partner_id = res_partner_obj.id
        # return
        return False

    @api.model
    def create(self, values):
        res = super(ExternalAddress, self).create(values)
        # Fix province_code
        if res.country_code and res.province_code:
            code_check = str(res.country_code)+'-'
            if code_check in res.province_code:
                res.province_code = res.province_code.replace(code_check, "")
        # operations
        res.operations_item()
        # return
        return res
