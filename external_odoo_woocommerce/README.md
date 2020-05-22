Realiza la integración sobre Woocommerce para integrarlo con el addon external_odoo_base y poder crear pedidos externos y albaranes externos

## odoo.conf
```
aws_access_key_id=xxxx
aws_secret_key_id=xxxxx
aws_region_name=eu-west-1
#external_odoo_woocommerce
sqs_external_sale_order_woocommerce_url=https://sqs.eu-west-1.amazonaws.com/381857310472/arelux-odoo-command-external-sale-order-woocommerce
sqs_external_stock_picking_woocommerce_url=https://sqs.eu-west-1.amazonaws.com/381857310472/arelux-odoo-command-external-stock-picking-woocommerce
```

## Crones

### SQS External Sale Order Woocommerce 
Frecuencia: cada 10 minutos

Descripción: Lee los mensajes del SQS y realiza todo el proceso de creación de pedido

nombre | version
--- | ---
arelux-odoo-command-external-sale-order-woocommerce | Prod
arelux-odoo_dev-command-external-sale-order-woocommerce | Dev

### SQS External Stock Picking Woocommerce 
Frecuencia: cada 10 minutos

Descripción: Lee los mensajes del SQS y realiza todo el proceso de creación de pedido

nombre | version
--- | ---
arelux-odoo-command-external-stock-picking-woocommerce | Prod
arelux-odoo_dev-command-external-stock-picking-woocommerce | Dev


### External Sale Order Update Shipping Expedition (Woocommerce) 
Frecuencia: cada hora

Descripción: Revisa los external_sale_order de los external_source_id que tengan integración por API, todas las expediciones que estén entregadas (y albaranes completados) y conectandose mediante API a WP actualizar el pedido al estado completado.
