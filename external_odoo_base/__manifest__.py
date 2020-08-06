# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "External Odoo",
    "version": "12.0.1.0.0",
    "author": "Odoo Nodriza Tech (ONT), "
              "Odoo Community Association (OCA)",
    "website": "https://nodrizatech.com/",
    "category": "Tools",
    "license": "AGPL-3",
    "depends": [
        "base",
        "sale",
        "account",
        "utm_websites",
        "delivery",
        "stock",
        "account_payment_mode",  # https://github.com/OCA/bank-payment
        "account_payment_partner",  # https://github.com/OCA/bank-payment
        "account_payment_sale",  # https://github.com/OCA/bank-payment
    ],
    "external_dependencies": {
        "python": [
            "boto3"
        ],
    },
    "data": [
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/external_odoo_view.xml",
    ],
    "installable": True
}
