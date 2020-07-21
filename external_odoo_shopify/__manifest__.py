# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
#sudo pip3 install --upgrade ShopifyAPI

{
    "name": "External Odoo Shopify",
    "version": "12.0.1.0.0",
    "author": "Odoo Nodriza Tech (ONT)",
    "website": "https://nodrizatech.com/",
    "category": "Tools",
    "license": "AGPL-3",
    "depends": [
        "external_odoo_base",
        "stock"
    ],
    "external_dependencies": {
        "python3" : [
            "ShopifyAPI",
            "boto3"
        ],
    },
    "data": [
        "data/ir_cron.xml",
        "views/external_sale_order.xml",
        "views/external_source.xml",
    ],
    "installable": True,
}