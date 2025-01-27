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
        template.cost_price_method = 'average'
        template.account_category = account_category
        product, = template.products
        product.cost_price = Decimal('5')
        template.save()
        product, = template.products

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
        purchase_line.quantity = 10.0
        purchase_line.unit_price = Decimal('10.0000')
        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.state, 'processing')
        self.assertEqual((purchase.lines[0].unit_price), (Decimal('10.0000')))

        # Validate Shipment
        Move = Model.get('stock.move')
        ShipmentIn = Model.get('stock.shipment.in')
        shipment = ShipmentIn()
        shipment.supplier = supplier

        for move in purchase.moves:
            incoming_move = Move(id=move.id)
            shipment.incoming_moves.append(incoming_move)
        shipment.save()
        self.assertEqual((shipment.incoming_moves[0].unit_price), (Decimal('10.0000')))
        product.reload()
        shipment.click('receive')
        self.assertEqual(product.cost_price, Decimal('10.0000'))
        shipment.click('do')

        #Create purchase with free of charge line and its in-shipment from its moves
        purchase = Purchase()
        purchase.party = supplier
        purchase.payment_term = payment_term
        purchase.invoice_method = 'shipment'
        purchase_line = purchase.lines.new()
        purchase_line.product = product
        purchase_line.quantity = 5.0
        purchase_line.unit_price = Decimal('10.0000')
        purchase_line.free_of_charge = True
        purchase.click('quote')
        purchase.click('confirm')
        self.assertEqual(purchase.lines[0].unit_price, Decimal('0.0000'))

        shipment = ShipmentIn()
        shipment.supplier = supplier
        for move in purchase.moves:
            incoming_move = Move(id=move.id)
            shipment.incoming_moves.append(incoming_move)
        shipment.save()
        #Move unit price is set to product's cost price
        self.assertEqual((shipment.incoming_moves[0].unit_price), (Decimal('10.0000')))
        product.reload()


        #Create a new purchase and receive another shipment inbetween so that the cost price is updated.
        purchase2 = Purchase()
        purchase2.party = supplier
        purchase2.payment_term = payment_term
        purchase2.invoice_method = 'shipment'
        purchase_line = purchase2.lines.new()
        purchase_line.product = product
        purchase_line.quantity = 10.0
        purchase_line.unit_price = Decimal('20.0000')
        purchase2.click('quote')
        purchase2.click('confirm')

        shipment2 = ShipmentIn()
        shipment2.supplier = supplier

        for move in purchase2.moves:
            incoming_move = Move(id=move.id)
            shipment2.incoming_moves.append(incoming_move)
        shipment2.save()
        shipment2.click('receive')
        product.reload()
        self.assertEqual(product.cost_price, Decimal('15.000'))
        shipment2.click('do')

        #Go back to free of charge shipment, and receive it.
        shipment.click('receive')
        #Move unit price is updated to product's cost price on reception, as to not alter the product's cost price average.
        self.assertEqual((shipment.incoming_moves[0].unit_price), (Decimal('15.0000')))
        product.reload()
        self.assertEqual(product.cost_price, Decimal('15.0000'))
        shipment.click('do')

        purchase.reload()
        self.assertEqual(purchase.shipment_state, 'received')

        # Check invoice lines, and free of charge line has not been generated. Whereas inbetween shipment has been invoiced as usual.
        free_of_charge_move = shipment.incoming_moves[0]
        self.assertEqual(len(free_of_charge_move.invoice_lines), 0)

        regular_move = shipment2.incoming_moves[0]
        self.assertEqual(len(regular_move.invoice_lines), 1)