from __future__ import division
from exchange import SellOrder, BuyOrder, Exchange


class Trader(object):

    def __init__(self, exchange, cash=0, tokens=0, strategy=None):
        assert isinstance(exchange, Exchange)
        self.ex = exchange
        self.cash = cash
        self.tokens = tokens
        self.strategy = strategy
        self._orders = []

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
            self.orders.remove(o)

    def trigger(self):
        self.strategy.trigger(self)

    @property
    def free_cash(self):
        return self.cash - sum(o.amount * o.price for o in self.orders if isinstance(o, BuyOrder))

    @property
    def free_tokens(self):
        return self.tokens - sum(o.amount for o in self.orders if isinstance(o, SellOrder))


class StrategyBase(object):

    def trigger(self, trader):
        pass

    def buy(self, trader, cash, price=None):
        ex = trader.ex
        if price:  # limit order
            amount = cash / price
            o = BuyOrder(price, amount, callback=trader.callback)
            ex.place(o)
        else:  # market order
            amount = ex.available(cash)
            ex.buy_market(amount)
            trader.cash -= cash
            trader.tokens += amount
        return amount

    def sell(self, trader, amount):  # mkt order
        assert trader.tokens >= amount
        cost = trader.ex.sell_market(amount)
        trader.cash += cost
        trader.tokens -= amount


class BuyAndHold(StrategyBase):
    "spends all cash to buy at market or limit"

    def __init__(self, price_limit=None):
        self.price = price_limit

    def trigger(self, trader):
        cash = trader.free_cash
        if cash:
            self.buy(cash)


class AverageIn(StrategyBase):
    "spends all cash to buy at market price over a certain period"

    def __init__(self, period, steps):
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

    def trigger(self, trader):
        if self.intervals is None:
            self._setup(trader)
        if self.intervals and self.intervals[0][0] <= trader.ex.time:
            start, cash = self.intervals.pop(0)
            self.buy(trader, cash)  # market order


class AverageOut(AverageIn):
    "sells all tokens at market price over a certain period"

    def _amount(self, trader):
        return trader.tokens / self.steps

    def trigger(self, trader):
        if self.intervals is None:
            self._setup(trader)
        if self.intervals and self.intervals[0][0] <= trader.ex.time:
            start, amount = self.intervals.pop(0)
            self.sell(trader, amount)  # market order


class TrailingStop(StrategyBase):
    "sells all tokens if price drops below a fraction of the max price seen"

    def __init__(self, max_loss_fraction=0.3):
        self.max_price = 0

    def trigger(self, trader):
        price = trader.ex.bid
        self.max_price = max(self.max_price, price)
        if price < self.max_price * (1 - self.max_loss_fraction):
            self.sell(trader, trader.tokens)


class TrendFollower(StrategyBase):
    "buys if if price is above a moving average, sells otherwise"
    def __init__(self, period):
        self.period = period

    def _ma(self, ex): # simple moving average
        oldest = ex.time - self.period
        prices = [t.price for t in ex.ticker if t.time > oldest]
        return sum(prices)/len(prices)

    def trigger(self, trader):
        ma = self._ma(trader.ex)
        if trader.cash and trader.ex.ask > ma: # buy signal
            self.buy(trader, trader.cash)
        elif trader.tokens and trader.ex.ask < ma: # sell signal
            self.sell(trader, trader.tokens)


class Arbitrageur(StrategyBase):
    """
    bridges ContinousToken and Exchange by selling/buying at market prices
    should not hold any tokens and have plenty of cash
    """
