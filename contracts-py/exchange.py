from __future__ import division
import bisect
from collections import namedtuple


class Order(object):

    def __init__(self, price, amount, callback=None):
        self.price = price
        self.amount = amount
        self._callback = callback
        self._original = (price, amount)

    def __cmp__(self, o):
        if self.price < o.price:
            return -1
        elif self.price > o.price:
            return 1
        return 0

    def execute(self, price, amount):
        assert amount <= self.amount
        self.amount -= amount
        self._callback(self, price, amount)

    def __repr__(self):
        return '<{}(price:{} amount:{})>'.format(self.__class__.__name__, self.price, self.amount)


assert Order(2, 1) > Order(1, 1) and Order(1, 1) < Order(2, 1) and Order(2, 1) == Order(2, 2)


class SellOrder(Order):
    pass


class BuyOrder(Order):
    pass


Tick = namedtuple('Tick', 'amount, price, time')


class NotAvailable(Exception):
    pass


class Exchange(object):

    def __init__(self):
        self._buy_orders = list()
        self._sell_orders = list()
        self.ticker = list()
        self.time = 0

    def update_time(self, time):
        self.time = time

    def place(self, o):
        if isinstance(o, BuyOrder):
            bisect.insort(self._buy_orders, o)
        else:
            assert isinstance(o, SellOrder)
            bisect.insort(self._sell_orders, o)
        self.match()

    def cancel(self, o):
        if isinstance(o, BuyOrder):
            self._buy_orders.remove(o)
        else:
            assert isinstance(o, SellOrder)
            self._sell_orders.remove(o)
        # print 'removed', o

    def _cleanup(self, o):
        if o.amount == 0:
            self.cancel(o)
            return True
        assert o.amount > 0

    def match(self):
        while (self._buy_orders and self._sell_orders):
            bo, so = self._buy_orders[-1], self._sell_orders[0]
            # print bo, so, bo >= so
            if not (bo >= so):
                break
            # match
            print 'match', bo, so
            amount = min(bo.amount, so.amount)
            price = (so.price + bo.price) / 2
            # update orders
            bo.execute(price, amount)
            so.execute(price, amount)
            # remove filled orders
            assert True in (self._cleanup(so), self._cleanup(bo))
            self.ticker.append(Tick(amount=amount, price=price, time=self.time))

    def _at_market(self, amount, lst, dryrun=False):
        assert amount > 0
        print '_at_market', amount, lst, dryrun
        # if amount > sum(o.amount for o in lst):
        #     s = sum(o.amount for o in lst)
        #     print s, amount, amount > s, type(s), type(amount), amount - s > 0
        #     raise NotAvailable()
        cost = 0
        for o in list(lst):
            a = min(amount, o.amount)
            amount -= a
            cost += a * o.price
            if not dryrun:
                o.execute(o.price, a)
                self._cleanup(o)
                self.ticker.append(Tick(amount=a, price=o.price, time=self.time))
            if amount == 0:
                break
        return cost

    def sell_market(self, amount, dryrun=False):
        return self._at_market(amount, list(reversed(self._buy_orders)), dryrun)

    def buy_market(self, amount, dryrun=False):
        return self._at_market(amount, self._sell_orders, dryrun)

    def sell_cost(self, amount):
        return self.sell_market(amount, dryrun=True)

    def buy_cost(self, amount):
        return self.buy_market(amount, dryrun=True)

    def buyable(self, cash, partial=True):
        amount = 0
        for o in self._sell_orders:
            a = min(o.amount, cash / o.price)
            amount += a
            cash -= a * o.price
            if cash == 0:
                break
        if cash > 0 and not partial:
            raise NotAvailable()
        return amount, cash

    def sellable(self, amount, partial=True):
        target = amount
        cash = 0
        for o in reversed(self._buy_orders):
            a = min(o.amount, amount)
            amount -= a
            cash += a * o.price
            if amount == 0:
                break
        if amount > 0 and not partial:
            raise NotAvailable()
        return target - amount, cash

    @property
    def bid(self):
        if not len(self._buy_orders):
            raise NotAvailable()
        return self._buy_orders[-1].price

    @property
    def ask(self):
        if not len(self._sell_orders):
            raise NotAvailable()
        return self._sell_orders[0].price

    @property
    def spread(self):
        return self.ask - self.bid


def test():

    ex = Exchange()

    def cb(o, price, amount):
        t = 'partial' if o.amount else 'filled'
        print '{} {} price:{} amount:{}'.format(t, o, price, amount)

    orders = []

    # gen non crossing book
    for price in range(100, 200, 10):
        o = SellOrder(price, amount=10, callback=cb)
        orders.append(o)

    for price in range(10, 100, 10):
        o = BuyOrder(price, amount=10, callback=cb)
        orders.append(o)

    print orders
    for o in orders:
        ex.place(o)

    # cross
    o = BuyOrder(price=101, amount=5, callback=cb)
    orders.append(o)
    ex.place(o)

    # cross multiple
    print
    o = BuyOrder(price=120, amount=14, callback=cb)
    orders.append(o)
    ex.place(o)

    # cross sell
    print
    o = SellOrder(price=85, amount=5, callback=cb)
    orders.append(o)
    ex.place(o)

    # cross sell multiple
    print
    o = SellOrder(price=75, amount=20, callback=cb)
    orders.append(o)
    ex.place(o)

    # buy market
    print
    cost = ex.buy_cost(50)
    cost2 = ex.buy_market(50)
    assert cost == cost2

    # sell market
    print
    cost = ex.sell_cost(50)
    cost2 = ex.sell_market(50)
    assert cost == cost2

    print ex.ticker

if __name__ == '__main__':
    test()
