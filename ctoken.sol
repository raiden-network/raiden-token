pragma solidity ^0.4.0;

contract Beneficiary {
    uint public fraction;

    function Beneficiary(uint issuance_fraction) {
        fraction = issuance_fraction;
    }
}

contract Auction {
    uint256 factor;
    uint256 const;
    uint256 elapsed = 0;

    function Auction(uint256 _factor, uint256 _const) {
        factor = _factor;
        _const = const;
    }

    function price_surcharge() returns(uint256 value) {
        return factor / elapsed + const;
    }
}

contract PriceSupplyCurve {
    uint256 factor;
    uint256 public base_price;

    function PriceSupplyCurve(uint256 _factor, uint256 _base_price) {
        factor = _factor;
        base_price = _base_price;
    }

    // supply - no of tokens?
    function price(uint256 _supply) returns (uint256 value) {
        return base_price + factor * _supply;
    }

    // sqrt implementation!
    function sqrt(uint256 _value) returns (uint256 value);

    // see what this calculates exactly
    function supply(uint256 _reserve) returns (uint256 value) {
        return (-base_price + sqrt(base_price**2 + 2 * factor * _reserve)) / factor;
    }

    function supply_at_price(uint256 _price) returns (uint256 value) {
        // assert price >= self.b
        if(_price < base_price)
            throw;

        return (_price - base_price) / factor;
    }

    function reserve(uint256 _supply) returns (uint256 value) {
        return base_price * _supply + factor / 2 * _supply**2;
    }

    function reserve_at_price(uint256 _price) returns (uint256 value) {
        // assert price >= 0
        if(_price < 0)
            throw;

        return reserve(supply_at_price(_price));
    }

    function cost(uint256 _supply, uint256 _num) returns (uint256 value) {
        return reserve(_supply + _num) - reserve(_supply);
    }

    function issued(uint256 _supply, uint256 _value) returns (uint256 value) {
        uint256 _reserve = reserve(_supply);
        return supply(_reserve + _value) - supply(_reserve);
    }
}


contract Token {

    //accounts (dict)

    function Token() {}

    // ERC20

    // supply
    function totalSupply() constant returns (uint256 supply) {
        // return sum(self.accounts.values())
    }

    function balanceOf(address _owner) constant returns (uint256 balance) {
        // return self.accounts.get(address, 0)
    }

    function transfer(address _to, uint256 _value) returns (bool success) {
        /*
        assert self.accounts[_from] >= value
        self.accounts[_from] -= value
        self.accounts[_to] += value
        */
    }

    function transferFrom(address _from, address _to, uint256 _value) returns (bool success);

    function approve(address _spender, uint256 _value) returns (bool success);
    function allowance(address _owner, address _spender) returns (uint256 value);

    event Transfer(address indexed _from, address indexed _to, uint256 _value);
    event Approval(address indexed _owner, address indexed _spender, uint256 _value);

    // Custom functions
    function issue(uint num, address recipient) {
        /*
        if recipient not in self.accounts:
            self.accounts[recipient] = 0
        self.accounts[recipient] += num
        */
    }

	function destroy(uint num, address owner) {
	    /*
	    if self.accounts[owner] < num:
            raise InsufficientFundsError('{} < {}'.format(self.accounts[owner], num))
        self.accounts[owner] -= num
        */
	}

}

contract ContinuousToken {
    PriceSupplyCurve curve;
    Auction auction;
    Beneficiary beneficiary;
    Token token = Token();
    uint256 reserve_value = 0;

    // uint80 constant None = uint80(0);

    function ContinuousToken(PriceSupplyCurve _curve, Beneficiary _beneficiary, Auction _auction) {
        curve = _curve;
        beneficiary = _beneficiary;
        auction = _auction;
    }

    // Helper functions
    function max(uint256 _a, uint256 _b) returns (uint256 value) {
        if(_a >= _b)
            return _a;
        return _b;
    }

    function min(uint256 _a, uint256 _b) returns (uint256 value) {
        if(_a <= _b)
            return _a;
        return _b;
    }

    function abs(uint256 _a, uint256 _b) returns (uint256 value) {

    }

    // almost_equal
    function xequal(uint256 _a, uint256 _b, uint256 threshold) returns (bool almost_equal) {
        // threshold = 0.0001;

        if(min(_a, _b) > 0) {
            //assert abs(a - b) / min(a, b) <= threshold, (a, b)
        }

        // assert abs(a - b) <= threshold, (a, b)
        return true;
    }

    function _notional_supply() returns (uint256 value) {
        /*
        supply according to reserve_value
        self.token.supply + self._skipped_supply"
        */
        return curve.supply(reserve_value);
    }

    function _skipped_supply() returns (uint256 value) {
        //tokens that were not issued, due to higher prices during the auction
        //assert self.token.supply <= self.curve.supply(self.reserve_value)
        if(token.totalSupply() > curve.supply(reserve_value))
            throw;

        return curve.supply(reserve_value) - token.totalSupply();
    }

    function _simulated_supply() returns (uint256 value) {
        /*
        current auction price converted to additional supply
        note: this is virtual skipped supply,
        so we must not include the skipped supply
        */
        if(auction.price_surcharge() >= curve.base_price) {
            uint256 s = curve.supply_at_price(auction.price_surcharge());
            return max(0, s - _skipped_supply());
        }
        return 0;
    }

    function _arithmetic_supply() returns (uint256 value) {
        return _notional_supply() + _simulated_supply();
    }

    // cost of selling, purchasing tokens
    function _sale_cost(uint256 _num) returns (uint256 value) {
        // assert num >= 0
        if(_num < 0)
            throw;

        uint256 added = _num / (1 - beneficiary.fraction);
        return curve.cost(_arithmetic_supply(), added);
    }

    function _purchase_cost_CURVE(uint256 _num) returns (uint256 value) {
        // the value offered if tokens are bought back
        // assert num >= 0 and num <= self.token.supply
        if(_num < 0 && _num > token.totalSupply())
            throw;

        uint256 c = -curve.cost(_arithmetic_supply(), -_num);
        return c;
    }

    // _purchase_cost_LINEAR
    function _purchase_cost(uint256 _num) returns (uint256 value) {
        // the value offered if tokens are bought back
        // assert num >= 0 and num <= self.token.supply
        if(_num < 0 && _num > token.totalSupply())
            throw;

        uint256 c = reserve_value * _num / token.totalSupply();
        return c;
    }

    //see how this works in Solidity
    // _purchase_cost = _purchase_cost_LINEAR;

    // Public functions

    function isauction() returns (uint256 value) {
        return _simulated_supply() > 0;
    }

    function create(uint256 _value, address _recipient) returns (uint256 value) {
        // recipient = None (default)

        uint256 s = _arithmetic_supply();
        uint256 issued = curve.issued(s, _value);
        uint256 sold = issued * (1 - beneficiary.fraction);
        uint256 seigniorage = issued - sold;  // FIXME implement limits

        token.issue(sold, _recipient);
        token.issue(seigniorage, beneficiary);
        reserve_value += _value;
        return sold;
    }

    function destroy(uint256 _num, address _owner) returns (uint256 value) {
        // _owner=None

        uint256 _value = _purchase_cost(_num);
        token.destroy(_num, _owner);  // can throw

        //assert value < self.reserve_value or xassert(value, self.reserve_value)
        if(_value > reserve_value || !xequal(_value, reserve_value))
            throw;

        _value = min(_value, reserve_value);
        reserve_value -= _value;
        return _value;
    }

    // Public const functions

    function ask() returns (uint256 value) {
        return _sale_cost(1);
    }

    function bid() returns (uint256 value) {
        if(!reserve_value)
            return 0;
        uint256 bid = _purchase_cost(1);
        //assert bid <= self.ask, (bid, self.ask)

        if(bid > ask())
            throw;

        return bid;
    }

    function curve_price_auction() returns (uint256 value) {
        return curve.cost(_arithmetic_supply(), 1);
    }

    function curve_price() returns (uint256 value) {
        return curve.cost(_notional_supply(), 1);
    }

    function mktcap() returns (uint256 value) {
        return ask() * token.totalSupply();
    }

    function valuation() returns (uint256 value) {
        return mktcap() - reserve_value();
    }

    function max_mktcap() returns (uint256 value) {
        uint256 vsupply = curve.supply_at_price(ask) - _skipped_supply();
        return ask() * vsupply;
    }

    function max_valuation() returns (uint256 value) {
        // FIXME
        return max_mktcap() * beneficiary.fraction;
    }

}
