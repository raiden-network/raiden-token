from __future__ import division
from exchange import SellOrder, BuyOrder, Exchange, NotAvailable
import random


class Trader(object):

    def __init__(self, exchange, cash=0, tokens=0, strategy=None):
        assert isinstance(exchange, Exchange)
        self.ex = exchange
        self.cash = cash
        self.tokens = tokens
        self.strategy = strategy
        self.pending = []  # pending orders

    def __repr__(self):
        return '<{} cash:{} tokens:{} strategy:{}'.format(self.__class__.__name__,
                                                          self.cash, self.tokens,
                                                          self.strategy)

    def callback(self, o, price, amount):
        if isinstance(o, SellOrder):
            self.cash += price * amount
            self.tokens -= amount
        else:
            assert isinstance(o, BuyOrder)
            self.cash -= price * amount
            self.tokens += amount
        assert self.cash >= 0
        assert self.tokens >= 0
        if o.amount == 0:
            try:
                self.pending.remove(o)
            except ValueError:
                pass  # FIXME

    def trigger(self):
        # print self, 'trigger', self.strategy
        self.strategy.trigger(self)

    @property
    def free_cash(self):
        return self.cash - sum(o.amount * o.price for o in self.pending if isinstance(o, BuyOrder))

    @property
    def free_tokens(self):
        return self.tokens - sum(o.amount for o in self.pending if isinstance(o, SellOrder))

    def place(self, o):
        self.ex.place(o)
        self.pending.append(o)

    def cancel(self, o):
        assert o in self.pending
        try:
            self.ex.cancel(o)
        except:
            print "WARNING, order not at ex", o

        self.pending.remove(o)


class StrategyBase(object):

    def __repr__(self):
        return '<{}>'.format(self.__class__.__name__)

    def trigger(self, trader):
        self._trigger(trader)
        # try:
        #     self._trigger(trader)
        # except NotAvailable:
        #     pass

    def buy(self, trader, cash, price=None):
        ex = trader.ex
        if price:  # limit order
            amount = cash / price
            o = BuyOrder(price, amount, callback=trader.callback)
            ex.place(o)
            trader.pending.append(o)
        else:  # market order
            amount, cost = ex.buyable(cash)
            if amount == 0:
                return 0
            ex.buy_market(amount)
            trader.cash -= cost
            trader.tokens += amount
        return amount

    def sell(self, trader, amount):  # mkt order
        assert trader.tokens >= amount
        amount, cost = trader.ex.sellable(amount)
        if amount == 0:
            return 0
        cost = trader.ex.sell_market(amount)
        trader.cash += cost
        trader.tokens -= amount
        return cost


class BuyAndHold(StrategyBase):
    "spends all cash to buy at market or limit"

    def __init__(self, price_limit=None):
        self.price = price_limit

    def _trigger(self, trader):
        cash = trader.free_cash
        if cash:
            # self.buy(trader, cash)
            # print trader.ex._sell_orders
            price = trader.ex.ask * 0.99
            amount = price / cash
            if amount < 1:
                return
            o = BuyOrder(price, amount, callback=trader.callback)
            trader.place(o)


class AverageIn(StrategyBase):
    "spends all cash to buy at market price over a certain period"

    def __init__(self, period=3600, steps=10):
        self.period = period
        self.steps = steps
        self.intervals = None

    def _amount(self, trader):
        return trader.cash / self.steps

    def _setup(self, trader):
        amount = self._amount(trader)
        self.intervals = []
        for i in range(self.steps):
            start = i * self.period / self.steps + trader.ex.time
            self.intervals.append((start, amount))

    def _trigger(self, trader):
        if self.intervals is None:
            self._setup(trader)
        if self.intervals and self.intervals[0][0] <= trader.ex.time:
            start, cash = self.intervals.pop(0)
            # self.buy(trader, cash)  # market order
            price = trader.ex.ask * 0.99
            amount = price / cash
            o = BuyOrder(price, amount, callback=trader.callback)
            trader.place(o)


class AverageOut(AverageIn):
    "sells all tokens at market price over a certain period"

    def _amount(self, trader):
        return trader.tokens / self.steps

    def _trigger(self, trader):
        if self.intervals is None:
            self._setup(trader)
        if self.intervals and self.intervals[0][0] <= trader.ex.time:
            start, amount = self.intervals.pop(0)
            # self.sell(trader, min(amount, trader.tokens))  # market order
            price = trader.ex.bid * 1.01
            o = SellOrder(price, amount, callback=trader.callback)
            trader.place(o)


class TrailingStop(StrategyBase):
    "sells all tokens if price drops below a fraction of the max price seen"

    def __init__(self, max_loss_fraction=0.3):
        self.max_price = 0
        self.max_loss_fraction = max_loss_fraction

    def _trigger(self, trader):
        try:
            price = trader.ex.bid
        except NotAvailable:
            return
        self.max_price = max(self.max_price, price)
        if price < self.max_price * (1 - self.max_loss_fraction):
            self.sell(trader, trader.tokens)


class TrendFollower(StrategyBase):
    "buys if if price is above a moving average, sells otherwise"

    def __init__(self, period=60):
        self.period = period

    def _ma(self, ex):  # simple moving average
        oldest = ex.time - self.period
        prices = [t.price for t in ex.ticker if t.time > oldest]
        if not prices:
            raise NotAvailable()
        return sum(prices) / len(prices)

    def _trigger(self, trader):
        try:
            ma = self._ma(trader.ex)
            price = trader.ex.ask
        except NotAvailable:
            return
        if trader.cash and price > ma:  # buy signal
            self.buy(trader, trader.cash)
        elif trader.tokens and price < ma:  # sell signal
            self.sell(trader, trader.tokens)


class MarketMaker(StrategyBase):
    """
    simulates price based on a random walk
    sets Bid and Ask offers
    """

    def __init__(self, start_price, mu, sigma):
        self.price = start_price
        self.mu = mu
        self.sigma = sigma

    def _trigger(self, trader):
        for o in list(trader.pending):  # delete old orders
            trader.cancel(o)
        self.price *= random.normalvariate(self.mu, self.sigma)
        ask = self.price * 1.01
        amount = trader.cash / self.price
        o = BuyOrder(self.price, amount, callback=trader.callback)
        trader.place(o)
        o = SellOrder(ask, trader.tokens, callback=trader.callback)
        trader.place(o)


class Arbitrageur(StrategyBase):
    """
    bridges ContinousToken and Exchange by selling/buying at market prices
    should not hold any tokens and have plenty of cash
    """


def test():
    random.seed(42)

    exchange = Exchange()

    max_tokens = 10000
    max_amount = 100 * max_tokens
    num_traders = 10
    traders = []
    strategies = [TrendFollower,
                  TrailingStop,
                  AverageIn,
                  AverageOut,
                  BuyAndHold]
    strategies = [BuyAndHold, AverageOut]
    # strategies = [BuyAndHold]

    mms = MarketMaker(start_price=100, mu=1, sigma=0.01)  # sigma is variate per tick
    market_maker = Trader(exchange, max_amount, max_tokens * num_traders, mms)
    traders.append(market_maker)

    for i in range(num_traders):
        amount = random.randint(0, max_amount)
        tokens = random.randint(0, max_tokens)
        strategy_cls = random.choice(strategies)
        trader = Trader(exchange, amount, tokens, strategy_cls())
        traders.append(trader)

    total_tokens = sum([t.tokens for t in traders])
    # bootstrap

    exchange.time = 1
    end_time = 3600
    interval = 10
    while exchange.time < end_time:
        exchange.time += interval
        for t in traders:
            t.trigger()

    print '\n'.join([str(x) for x in exchange.ticker])
    print exchange._sell_orders
    print exchange._buy_orders

    print traders

    total_tokens2 = sum([t.tokens for t in traders])
    assert total_tokens2 == total_tokens, (total_tokens2, total_tokens)

if __name__ == '__main__':
    test()
