# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "External Odoo Woocommerce",
    "version": "12.0.1.0.0",
    "author": "Odoo Nodriza Tech (ONT), "
              "Odoo Community Association (OCA)",
    "website": "https://nodrizatech.com/",
    "category": "Tools",
    "license": "AGPL-3",
    "depends": [
        "external_odoo_base"
    ],
    "external_dependencies": {
        "python": [
            "woocommerce",
            "boto3"
        ],
    },
    "data": [
        "data/ir_cron.xml",
    ],
    "installable": True
}
