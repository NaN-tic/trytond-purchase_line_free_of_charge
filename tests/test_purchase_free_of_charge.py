import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules, set_user


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):


        # Activate modules
        activate_modules('purchase_line_free_of_charge')

        # Create company
        _ = create_company()
        company = get_company()

        # Create purchase user
        User = Model.get('res.user')
        Group = Model.get('res.group')
        purchase_user = User()
        purchase_user.name = 'Purchase'
        purchase_user.login = 'purchase'
        purchase_group, = Group.find([('name', '=', 'Purchase')])
        purchase_user.groups.append(purchase_group)
        stock_group, = Group.find([('name', '=', 'Stock')])
        purchase_user.groups.append(stock_group)
        purchase_user.save()

        # Create account user
        account_user = User()
        account_user.name = 'Account'
        account_user.login = 'account'
        account_user.save()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.purchasable = True
        template.list_price = Decimal('10')
        template.account_category = account_category
        template.save()
        product, = template.products
        product.cost_price = Decimal('10.0000')
        product.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # purchase some products
        set_user(purchase_user)
        Purchase = Model.get('purchase.purchase')
        purchase = Purchase()
        purchase.party = supplier
        purchase.payment_term = payment_term
        purchase.invoice_method = 'shipment'
        purchase_line = purchase.lines.new()
        purchase_line.product = product
        purchase_line.unit_price = Decimal('5.0000')
        purchase_line.quantity = 5.0
        purchase_line = purchase.lines.new()
        purchase_line.product = product
        purchase_line.unit_price = Decimal('5.0000')
        purchase_line.quantity = 2.0
        purchase_line.free_of_charge = True
        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.state, 'processing')
        # First one is a regular purchase line. Second one is free of charge.
        self.assertEqual((purchase.lines[0].unit_price, purchase.lines[1].unit_price), (Decimal('5.0000'), Decimal('0.0000')))

        # Validate Shipments
        Move = Model.get('stock.move')
        ShipmentIn = Model.get('stock.shipment.in')
        shipment = ShipmentIn()
        shipment.supplier = supplier

        for move in purchase.moves:
            incoming_move = Move(id=move.id)
            shipment.incoming_moves.append(incoming_move)

        shipment.save()
        # First move comes from regular purchase line. Second move comes from free of charge purchase line.
        self.assertEqual(shipment.origins, purchase.rec_name)
        shipment.click('receive')
        shipment.click('do')
        self.assertEqual((shipment.incoming_moves[0].unit_price, shipment.incoming_moves[1].unit_price), (Decimal('5.0000'), Decimal('10.0000')))

        purchase.reload()
        self.assertEqual(purchase.shipment_state, 'received')
        self.assertEqual(len(purchase.shipments), 1)

        move = shipment.incoming_moves[0]
        free_of_charge_move = shipment.incoming_moves[1]
        self.assertEqual(len(move.invoice_lines), 1)
        self.assertEqual(len(free_of_charge_move.invoice_lines), 0)
