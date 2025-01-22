from trytond.pool import PoolMeta
from trytond.model import fields
from trytond.pyson import Eval


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    charge_free = fields.Boolean('Free of Charge', states={
        'readonly': Eval('purchase_state') != 'draft'})

    @fields.depends('charge_free', 'product', 'unit_price')
    def on_change_charge_free(self):
        if self.charge_free:
            if self.product:
                self.unit_price = 0

    def get_invoice_line(self):
        if self.charge_free:
            return []
        return super().get_invoice_line()

    def get_move(self, move_type):
        move = super().get_move(move_type)
        if move and self.charge_free and self.product:
            move.unit_price = self.product.cost_price
        return move