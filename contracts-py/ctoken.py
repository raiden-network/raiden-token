from __future__ import division
from math import sqrt


def assert_almost_equal(a, b, threshold=0.0001):
    if min(a, b) > 0:
        assert abs(a - b) / min(a, b) <= threshold, (a, b)
    assert abs(a - b) <= threshold, (a, b)
    return True


xassert = assert_almost_equal


class InsufficientFundsError(Exception):
    pass


class Beneficiary(object):

    def __init__(self, issuance_fraction=0):
        self.fraction = issuance_fraction


class Token(object):

    def __init__(self):
        self.accounts = dict()

    @property
    def supply(self):
        return sum(self.accounts.values())

    def issue(self, num, recipient):
        if recipient not in self.accounts:
            self.accounts[recipient] = 0
        self.accounts[recipient] += num

    def destroy(self, num, owner):
        if self.accounts[owner] < num:
            raise InsufficientFundsError('{} < {}'.format(self.accounts[owner], num))
        self.accounts[owner] -= num

    def transfer(self, _from, _to, value):
        assert self.accounts[_from] >= value
        self.accounts[_from] -= value
        self.accounts[_to] += value

    def balanceOf(self, address):
        return self.accounts.get(address, 0)


class Auction(object):

    def __init__(self, factor, const):
        self.factor = factor
        self.const = const
        self.elapsed = 0

    @property
    def price_surcharge(self):
        return self.factor / (self.elapsed + self.const)


class PriceSupplyCurve(object):

    def __init__(self, factor=1., base_price=0):
        self.f = factor
        self.b = base_price

    def price(self, supply):
        return self.b + self.f * supply

    def supply(self, reserve):
        return (-self.b + sqrt(self.b**2 + 2 * self.f * reserve)) / self.f

    def supply_at_price(self, price):
        assert price >= self.b
        return (price - self.b) / self.f

    def reserve(self, supply):
        return self.b * supply + self.f / 2 * supply**2

    def reserve_at_price(self, price):
        assert price >= 0
        return self.reserve(self.supply_at_price(price))

    def cost(self, supply, num):
        return self.reserve(supply + num) - self.reserve(supply)

    def issued(self, supply, value):
        reserve = self.reserve(supply)
        return self.supply(reserve + value) - self.supply(reserve)


class ContinuousToken(object):

    def __init__(self, curve, beneficiary, auction):
        self.curve = curve
        self.auction = auction
        self.beneficiary = beneficiary
        self.auction = auction
        self.token = Token()
        self.reserve_value = 0

    # supplies

    @property
    def _notional_supply(self):
        """"
        supply according to reserve_value
        self.token.supply + self._skipped_supply"
        """
        return self.curve.supply(self.reserve_value)

    @property
    def _skipped_supply(self):
        "tokens that were not issued, due to higher prices during the auction"
        assert self.token.supply <= self.curve.supply(self.reserve_value)
        return self.curve.supply(self.reserve_value) - self.token.supply

    @property
    def _simulated_supply(self):
        """
        current auction price converted to additional supply
        note: this is virtual skipped supply,
        so we must not include the skipped supply
        """
        if self.auction.price_surcharge >= self.curve.b:
            s = self.curve.supply_at_price(self.auction.price_surcharge)
            return max(0, s - self._skipped_supply)
        return 0

    @property
    def _arithmetic_supply(self):
        return self._notional_supply + self._simulated_supply

    # cost of selling, purchasing tokens

    def _sale_cost(self, num):  # cost
        assert num >= 0
        added = num / (1 - self.beneficiary.fraction)
        return self.curve.cost(self._arithmetic_supply, added)

    def _purchase_cost_CURVE(self, num):
        "the value offered if tokens are bought back"
        assert num >= 0 and num <= self.token.supply
        c = -self.curve.cost(self._arithmetic_supply, -num)
        return c

    def _purchase_cost_LINEAR(self, num):
        "the value offered if tokens are bought back"
        assert num >= 0 and num <= self.token.supply
        c = self.reserve_value * num / self.token.supply
        return c

    _purchase_cost = _purchase_cost_LINEAR

    # public functions

    @property
    def isauction(self):
        return self._simulated_supply > 0

    def create(self, value, recipient=None):
        s = self._arithmetic_supply
        issued = self.curve.issued(s, value)
        sold = issued * (1 - self.beneficiary.fraction)
        seigniorage = issued - sold  # FIXME implement limits
        self.token.issue(sold, recipient)
        self.token.issue(seigniorage, self.beneficiary)
        self.reserve_value += value
        return sold

    def destroy(self, num, owner=None):
        value = self._purchase_cost(num)
        self.token.destroy(num, owner)  # can throw
        assert value < self.reserve_value or xassert(value, self.reserve_value)
        value = min(value, self.reserve_value)
        self.reserve_value -= value
        return value

    # public const functions

    @property
    def ask(self):
        return self._sale_cost(1)

    @property
    def bid(self):
        if not self.reserve_value:
            return 0
        bid = self._purchase_cost(1)
        assert bid <= self.ask, (bid, self.ask)
        return bid

    @property
    def curve_price_auction(self):
        return self.curve.cost(self._arithmetic_supply, 1)

    @property
    def curve_price(self):
        return self.curve.cost(self._notional_supply, 1)

    @property
    def mktcap(self):
        return self.ask * self.token.supply

    @property
    def valuation(self):  # (ask - bid) * supply
        return self.mktcap - self.reserve_value

    @property
    def max_mktcap(self):
        vsupply = self.curve.supply_at_price(self.ask) - self._skipped_supply
        return self.ask * vsupply

    @property
    def max_valuation(self):  # FIXME
        return self.max_mktcap * self.beneficiary.fraction

    # def valuation_after_create(self, value):
    #     # calc supply after adding value
    #     reserve = self.reserve_value + value
    #     vsa = self.curve.supply(reserve) + self._simulated_supply  # FIXME at crossing
    #     ask = self.curve.cost(vsa, 1)
    #     issued = vsa - self._arithmetic_supply
    #     supply = self.token.supply + issued
    #     mktcap = ask * supply
    #     valuation = mktcap - reserve
    #     return valuation
