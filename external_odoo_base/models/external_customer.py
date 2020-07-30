# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ExternalCustomer(models.Model):
    _name = 'external.customer'
    _description = 'External Customer'
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

    external_url = fields.Char(
        compute='_compute_external_url',
        string='External Url',
        store=False
    )

    @api.multi
    @api.depends('external_source_id', 'external_id')
    def _compute_external_url(self):
        self.ensure_one()
        self.external_url = ''
        if self.external_source_id.type == 'shopify':
            self.external_url = 'https://%s/admin/customers/%s' % (
                self.external_source_id.url,
                self.external_id
            )
    # fields
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
    @api.depends('partner_id')
    def action_operations_item(self):
        for item in self:
            if item.partner_id:
                item.action_operations_item()

    @api.multi
    def operations_item(self):
        for item in self:
            if item.partner_id:
                # phone
                phone = None
                mobile = None
                # phone_mobile
                if item.phone:
                    # phone vs mobile
                    phone = str(item.phone)
                    mobile = None
                    phone_first_char = str(item.phone)[:1]
                    if phone_first_char == '6':
                        mobile = str(phone)
                        phone = None
                    # search
                    if phone:
                        items = self.env['res.partner'].sudo().search(
                            [
                                ('type', '=', 'contact'),
                                ('email', '=', str(item.email)),
                                ('active', '=', True),
                                ('supplier', '=', False),
                                ('phone', '=', str(phone))
                            ]
                        )
                    else:
                        items = self.env['res.partner'].sudo().search(
                            [
                                ('type', '=', 'contact'),
                                ('email', '=', str(item.email)),
                                ('active', '=', True),
                                ('supplier', '=', False),
                                ('mobile', '=', str(mobile))
                            ]
                        )
                else:
                    items = self.env['res.partner'].sudo().search(
                        [
                            ('email', '=', str(item.email)),
                            ('active', '=', True),
                            ('supplier', '=', False)
                        ]
                    )
                # if exists
                if items:
                    item.partner_id = items[0].id
                    # Update country_id
                    if item.partner_id.country_id:
                        item.country_id = item.partner_id.country_id.id
                    # Update state_id
                    if item.partner_id.state_id:
                        item.country_state_id = item.partner_id.state_id.id
                else:
                    # name
                    name = item.first_name
                    if item.last_name:
                        name = "%s %s" % (
                            item.first_name,
                            item.last_name
                        )
                    # create
                    vals = {
                        'active': True,
                        'customer': True,
                        'supplier': False,
                        'name': str(name),
                        'street': str(item.address_1),
                        'city': str(item.city)
                    }
                    # address_2
                    if item.address_2:
                        vals['street2'] = str(item.address_2)
                    # zip
                    if item.postcode:
                        vals['zip'] = str(item.postcode)
                    # email
                    if item.email:
                        vals['email'] = str(item.email)
                    # phone_mobile
                    if phone:
                        vals['phone'] = str(phone)
                    else:
                        vals['mobile'] = str(mobile)
                    # vat
                    if item.vat:
                        vals['vat'] = 'EU'+str(item.vat)
                    # country_id
                    if item.country_code:
                        items = self.env['res.country'].sudo().search(
                            [
                                ('code', '=', str(item.country_code))
                            ]
                        )
                        if items:
                            # country_id
                            item.country_id = items[0].id
                            vals['country_id'] = items[0].id
                            # state_id
                            if item.province_code:
                                items = self.env['res.country.state'].sudo().search(
                                    [
                                        ('country_id', '=', item.country_id.id),
                                        ('code', '=', str(item.province_code))
                                    ]
                                )
                                if items:
                                    # state_id
                                    item.country_state_id = items[0].id
                                    vals['state_id'] = items[0].id
                                else:
                                    if item.postcode:
                                        items = self.env[
                                            'res.better.zip'
                                        ].sudo().search(
                                            [
                                                ('country_id', '=', item.country_id.id),
                                                ('name', '=', str(item.postcode))
                                            ]
                                        )
                                        if items:
                                            zip = items[0]
                                            if zip.state_id:
                                                # update_state_id
                                                item.country_state_id = zip.state_id.id
                                                vals['state_id'] = zip.state_id.id
                    # create
                    res_partner_obj = item.env['res.partner'].create(vals)
                    item.partner_id = res_partner_obj.id
        # return
        return False

    @api.model
    def create(self, values):
        res = super(ExternalCustomer, self).create(values)
        # Fix province_code
        if res.country_code and res.province_code:
            code_check = str(res.country_code)+'-'
            if code_check in res.province_code:
                res.province_code = res.province_code.replace(code_check, "")
        # operations
        res.operations_item()
        # return
        return res
