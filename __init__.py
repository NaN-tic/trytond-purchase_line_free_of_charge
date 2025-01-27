# This file is part purchase_line_free_of_charge module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import purchase
from . import stock

def register():
    Pool.register(
        purchase.PurchaseLine,
        stock.Move,
        module='purchase_line_free_of_charge', type_='model')
    Pool.register(
        module='purchase_line_free_of_charge', type_='wizard')
    Pool.register(
        module='purchase_line_free_of_charge', type_='report')
