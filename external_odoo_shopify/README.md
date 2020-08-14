Realiza la integración sobre Shopify para integrarlo con el addon external_odoo_base y poder crear pedidos externos

## odoo.conf
- aws_access_key_id=xxxx
- aws_secret_key_id=xxxxx
- aws_region_name=eu-west-1
- #external_odoo_woocommerce
- sqs_external_sale_order_shopify_url=https://sqs.eu-west-1.amazonaws.com/381857310472/arelux-odoo-command-external-sale-order-shopify

## Crones

### SQS External Sale Order Shopify 
Frecuencia: cada 10 minutos

Descripción: Lee los mensajes del SQS y realiza todo el proceso de creación de pedido

nombre | version
--- | ---
arelux-odoo-command-external-sale-order-shopify | Dev
arelux-odoo_dev-command-external-sale-order-shopify | Prod

### External Product Stock Sync (Shopify)
Frecuencia: 1 vez al día

Descripción: Respecto a los productos de shopify que tienen marcado el "Stock Sync" y que tienen vinculado un producto de Odoo se actualizará en Shopify respecto al location_id definido a nivel de external_source el stock que existan en ese momento en Odoo.

### External Sale Order Update Shipping Expedition (Shopify) 
Frecuencia: cada hora

Descripción: Revisa los external_sale_order de los external_source_id que tengan integración por API, todas las expediciones que estén entregadas (y albaranes completados) y conectandose mediante API a Shopify define un fulfillment para el pedido para dejarlo como ‘preparado’
