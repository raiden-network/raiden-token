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
        self.per_step = 0
        self.last = None

    def trigger(self, trader):
        if not self.last:
            self.start = trader.ex.time
        cash = trader.free_cash


class AverageOut(StrategyBase):
    "sells all tokens at market price over a certain period"


class TrailingStop(StrategyBase):
    "sells tokens if price drops below a fraction of the max price seen"


class TrendFollower(StrategyBase):
    "buys if if price is above a moving average, sells otherwise"


class Arbitrageur(StrategyBase):
    """
    bridges ContinousToken and Exchange by selling/buying at market prices
    should not hold any tokens and have plenty of cash
    """
