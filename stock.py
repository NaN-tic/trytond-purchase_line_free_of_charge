from trytond.pool import Pool, PoolMeta


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    @classmethod
    def do(cls, moves):
        PurchaseLine = Pool().get('purchase.line')
        for move in moves:
            if move.origin and isinstance(move.origin, PurchaseLine):
                if move.origin.free_of_charge and move.product:
                    move.unit_price = move.product.cost_price
        super().do(moves)