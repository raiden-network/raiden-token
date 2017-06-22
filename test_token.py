from __future__ import division

from token import Beneficiary, Auction
from token import PriceSupplyCurve, ContinuousToken, xassert


def test_curve():
    curve = PriceSupplyCurve(factor=0.0001, base_price=5)
    assert curve.supply(0) == 0
    assert curve.price(0) == curve.b
    assert curve.supply_at_price(curve.b) == 0, curve.supply_at_price(curve.b)
    assert curve.reserve_at_price(curve.b) == 0
    assert curve.reserve(0) == 0

    supply = 1000000
    price = curve.price(supply)
    assert curve.supply_at_price(price) == supply
    reserve = curve.reserve(supply)
    assert curve.reserve_at_price(price) == reserve
    num = 1000
    value = curve.cost(supply, num)
    assert value > 0
    xassert(num, curve.issued(supply, value))
    num = -1000
    value = curve.cost(supply, num)
    assert value < 0
    assert num == curve.issued(supply, value)
    assert -curve.cost(supply, -1) < curve.cost(supply, 1)  # bid < ask


test_curve()


def test_auction_sim():
    curve = PriceSupplyCurve(factor=0.0001, base_price=5)
    auction = Auction(factor=10**5, const=10**3)
    beneficiary = Beneficiary(issuance_fraction=0.2)
    ct = ContinuousToken(curve, beneficiary, auction)

    buys = [i * 1000 for i in range(1, 10)]
    totalcost = 0
    for num in buys:
        auction.elapsed += 3600
        # buy tokens
        ask = ct.ask
        bid = ct.bid
        cost = ct._sale_cost(num)
        totalcost += cost
        sold = ct.create(cost)
        mode = 'A' if ct.isauction else 'T'
        rt = ct.reserve_value / ct.token.supply
        s = 'bought:{} {} @ {:.2f} {:.2f}\tcost:{:.0f} mktcap:{:.0f} reserve:{:.0f} rt:{:.2f}'
        print s.format(mode, sold, bid, ask, cost, ct.mktcap, ct.reserve_value, rt)

    print 'totalcost', totalcost
    assert totalcost == ct.reserve_value
    # sell tokens
    num = sum(buys)
    print num
    pcost = ct._purchase_cost(num)
    # xassert(pcost, totalcost)
    received = ct.destroy(num)
    xassert(received, pcost)
    print "sold:", num, "for:", received, "ask:", ct.ask, ct.isauction

    # sell tokens
    rt = ct.reserve_value / ct.token.supply
    print 'reserve/token', rt
    num = ct.token.supply
    print num
    pcost = ct._purchase_cost(num)
    assert pcost == ct.reserve_value, (pcost, ct.reserve_value)
    # xassert(pcost, totalcost)
    received = ct.destroy(num, beneficiary)
    xassert(received, pcost)
    print "sold:", num, "for:", received, "ask:", ct.ask, ct.isauction
    assert ct.token.supply == 0
    assert ct.reserve_value == 0, ct.reserve_value


def test_auction_raw():
    curve = PriceSupplyCurve(factor=0.0001, base_price=5)
    auction = Auction(factor=10**5, const=10**3)
    beneficiary = Beneficiary(issuance_fraction=0)
    ct = ContinuousToken(curve, beneficiary, auction)
    assert ct._vsupply == 0

    # buy tokens
    num = 1
    tcost = curve.cost(ct._vsupply_auction, num)
    cost = ct._sale_cost(num)
    assert cost == tcost
    sold = ct.create(cost)
    assert sold == num and num == ct.token.supply

    # sell tokens
    pcost = ct._purchase_cost(num)
    xassert(pcost, cost)
    received = ct.destroy(num)
    xassert(received, pcost)


def test_auction():
    curve = PriceSupplyCurve(factor=0.0001, base_price=5)
    auction = Auction(factor=10**5, const=10**3)
    beneficiary = Beneficiary(issuance_fraction=0)
    ct = ContinuousToken(curve, beneficiary, auction)
    assert ct.ask > auction.price_surcharge
    ask = ct.ask
    print 'ask', ask
    # xassert(ask, ct.curve.cost(0, 1) / (1 - beneficiary.fraction))
    assert ct._sale_cost(1) == ask

    # buy tokens
    num = 1000
    cost = ct._sale_cost(num)
    assert cost > ask * num
    sold = ct.create(cost)
    xassert(sold, num)
    xassert(num, ct.token.supply)
    print 'bought:', sold, 'at ask:', ask, ' cost:', cost, 'ask after:', ct.ask
    assert ct.token.supply == sold
    assert ct._vsupply >= ct.token.supply, (ct._vsupply, ct.token.supply)
    assert ct.reserve_value == cost
    assert ct.ask > auction.price_surcharge
    assert ct.bid < ct.ask, (ct.bid, ct.ask)
    print 'ask', ct.ask, 'bid', ct.bid
    assert ct.ask > ask

    # sell tokens
    num = ct.token.supply
    pcost = ct._purchase_cost(num)
    xassert(pcost, cost)
    received = ct.destroy(num)
    xassert(received, pcost)
    print "sold:", num, "for:", received, "ask:", ct.ask


def test():
    curve = PriceSupplyCurve(factor=0.0001, base_price=5)
    auction = Auction(factor=0, const=10**3)  # disabled
    beneficiary = Beneficiary(issuance_fraction=0)  # disabled
    ct = ContinuousToken(curve, beneficiary, auction)
    ask = ct.ask
    assert ct._sale_cost(1) == ask
    num = 1000
    cost = ct._sale_cost(num)
    assert cost > ask * num
    sold = ct.create(cost)
    xassert(sold, num)
    assert ct.token.supply == sold
    assert ct.token.supply == ct.curve.supply(ct.reserve_value)
    assert ct._skipped_supply == 0, ct._skipped_supply
    assert ct._vsupply == ct.token.supply
    assert ct.token.accounts[None] == sold
    assert ct._vsupply == ct.token.supply, (ct._vsupply, ct.token.supply)
    assert ct.reserve_value == cost
    assert ct.ask > ask
    assert ct.bid < ct.ask, (ct.bid, ct.ask)
    xassert(ct.token.supply, num)
    pcost = ct._purchase_cost(ct.token.supply)
    xassert(pcost, cost)
    received = ct.destroy(num)
    assert ct.token.supply >= 0
    xassert(ct.token.supply, 0)
    assert ct._vsupply == 0
    assert ct.ask == ask


def test_beneficiary():
    curve = PriceSupplyCurve(factor=0.0001, base_price=5)
    auction = Auction(factor=0, const=10**3)  # disabled
    beneficiary = Beneficiary(issuance_fraction=.20)
    ct = ContinuousToken(curve, beneficiary, auction)
    ask = ct.ask
    xassert(ask, ct.curve.cost(0, 1) / (1 - beneficiary.fraction))
    assert ct._sale_cost(1) == ask
    # buy
    num = 1000
    cost = ct._sale_cost(num)
    assert cost > ask * num
    sold = ct.create(cost)
    # check
    xassert(sold, num)
    assert ct.token.supply == sold / (1 - beneficiary.fraction)
    assert ct.token.accounts[None] == sold
    assert ct.token.accounts[beneficiary] == ct.token.supply - sold
    num_beneficiary = ct.token.accounts[beneficiary]
    assert ct._vsupply >= ct.token.supply, (ct._vsupply, ct.token.supply)
    assert ct.reserve_value == cost
    assert ct.ask > ask
    assert ct.bid < ct.ask, (ct.bid, ct.ask)
    pcost = ct._purchase_cost(ct.token.supply)
    assert pcost == cost

    # sell buyers part
    ask = ct.ask
    pcost = ct._purchase_cost(num)
    received = ct.destroy(num)
    xassert(received, pcost)
    assert ct.token.supply == num_beneficiary
    assert ct.ask < ask

    # sell beneficiary part
    assert num_beneficiary == ct.token.accounts[beneficiary]
    ask = ct.ask
    pcost = ct._purchase_cost(num_beneficiary)
    received = ct.destroy(num_beneficiary, beneficiary)
    xassert(received, pcost)
    assert ct.token.supply == 0
    xassert(ct._vsupply, ct.token.supply)
    assert ct.ask < ask


def test_auction_with_beneficiary():
    curve = PriceSupplyCurve(factor=0.0001, base_price=5)
    auction = Auction(factor=10**6, const=10**3)
    beneficiary = Beneficiary(issuance_fraction=.20)
    ct = ContinuousToken(curve, beneficiary, auction)
    ask = ct.ask
    assert ct._sale_cost(1) == ask
    # buy
    num = 1000
    cost = ct._sale_cost(num)
    assert cost > ask * num
    sold = ct.create(cost)
    # check
    xassert(sold, num)
    assert ct.token.supply == sold / (1 - beneficiary.fraction)
    assert ct.token.accounts[None] == sold
    assert ct.token.accounts[beneficiary] == ct.token.supply - sold
    num_beneficiary = ct.token.accounts[beneficiary]
    assert ct._vsupply >= ct.token.supply, (ct._vsupply, ct.token.supply)
    assert ct.reserve_value == cost
    assert ct.ask > ask
    assert ct.bid < ct.ask, (ct.bid, ct.ask)
    pcost = ct._purchase_cost(ct.token.supply)
    assert pcost == cost

    # sell buyers part
    ask = ct.ask
    pcost = ct._purchase_cost(num)
    received = ct.destroy(num)
    xassert(received, pcost)
    assert ct.token.supply == num_beneficiary
    assert ct.ask < ask

    # sell beneficiary part
    assert num_beneficiary == ct.token.accounts[beneficiary]
    ask = ct.ask
    pcost = ct._purchase_cost(num_beneficiary)
    received = ct.destroy(num_beneficiary, beneficiary)
    xassert(received, pcost)
    assert ct.token.supply == 0
    xassert(ct._vsupply, ct.token.supply)
    assert ct.ask < ask


test()
test_beneficiary()
test_auction_raw()
test_auction()
test_auction_with_beneficiary()
print
test_auction_sim()
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
