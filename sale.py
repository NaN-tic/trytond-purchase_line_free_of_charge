from trytond.pool import PoolMeta
from trytond.model import fields
import decimal


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    free = fields.Boolean('Free of Charge')

    @fields.depends(
    'type', 'quantity', 'unit_price',
    'sale', '_parent_sale.currency', 'free', 'product')
    def on_change_with_amount(self):
        if not self.free:
            return super().on_change_with_amount()
        if self.product and self.product.cost_price:
            self.unit_price = 0
            return self.product.cost_price * self.quantity
        return 0

    @fields.depends('free')
    def on_change_with_free(self):
        self.on_change_with_amount()
        return self.free

    @fields.depends('free', 'unit_price', 'product')
    def on_change_with_unit_price(self):
        if self.free:
            if self.product:
                return (self.product.cost_price or 0) * decimal.Decimal(self.quantity)
        return self.unit_price
