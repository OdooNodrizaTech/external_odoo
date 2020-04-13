Permite pedidos externos y albaranes externos

En el apartado Configuración > Técnico se añade el apartado External Odoo con los siguientes elementos del menú:

- Product
- Customer
- Stock picking
- Address
- Sale Order
- Source

## Crones

### External Stock Picking Line Generate Invoice Lines

Serviría para auto-generar facturas borrador con tantas líneas como líneas validadas de AV.

Adicionalmente JUSTO antes de validar una factura de clientes (type=out_invoice) se buscan todas las líneas de la factura para buscar las líneas de pedidos de venta y por consiguiente los pedidos de venta (sale_order).
Con los pedidos de venta encontrados se buscará si hacen referencia a algún pedidos externo (external_sale_order) para que si fuera el caso, se sumaran los importes totales de todos los pedidos y se mirara si existe diferencia respecto al total de la factura.
En caso de que exista diferencia (positiva o negativa) se aplicará esa diferencia en el importe (amount) de las 1ª línea de impuesto de la factura para que cuadraran los importes correctamente.
