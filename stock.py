from trytond.pool import Pool, PoolMeta


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    @classmethod
    def do(cls, moves):
        PurchaseLine = Pool().get('purchase.line')
        to_save = []
        for move in moves:
            if move.origin and isinstance(move.origin, PurchaseLine):
                if move.origin.free_of_charge and move.product:
                    move.unit_price = move.product.cost_price
                    to_save.append(move)
        cls.save(to_save)
        super().do(moves)