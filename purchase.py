from trytond.pool import PoolMeta
from trytond.model import fields
from trytond.pyson import Eval


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    free_of_charge = fields.Boolean('Free of Charge', states={
        'readonly': Eval('purchase_state') != 'draft'})

    @fields.depends('free_of_charge', 'product', 'unit_price')
    def on_change_free_of_charge(self):
        if self.free_of_charge:
            if self.product:
                self.unit_price = 0

    def get_invoice_line(self):
        if self.free_of_charge:
            return []
        return super().get_invoice_line()

    def get_move(self, move_type):
        move = super().get_move(move_type)
        if move and self.free_of_charge:
            move.unit_price = self.product.cost_price
        return move