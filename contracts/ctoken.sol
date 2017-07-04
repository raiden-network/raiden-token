pragma solidity ^0.4.11;

import './token.sol';
import './auction.sol';
import './safe_math.sol';
import './utils.sol';

contract ContinuousToken is StandardToken {

    string constant public name = 'Continuous Token';
    string constant public symbol = ''; // TODO
    uint8 constant public decimals = 18; // TODO

    // Amount of currency raised from selling/issuing tokens
    // Cumulated sales price
    uint public reserve_value = 0;
    uint public base_price;
    uint public price_factor;
    uint public price_factor_dec;
    uint beneficiary_fr;
    uint beneficiary_fr_dec;
    Auction auction;
    address public beneficiary;

    // TODO preassigned tokens ?
    function ContinuousToken(
        address _auction,
        uint _base_price,
        uint _price_factor,
        uint _price_factor_dec,
        uint _beneficiary_fr,
        uint _beneficiary_fr_dec)
    {
        auction = Auction(_auction);
        beneficiary = msg.sender;
        base_price = _base_price;
        price_factor = _price_factor;
        price_factor_dec = _price_factor_dec;
        beneficiary_fr = _beneficiary_fr;
        beneficiary_fr_dec = _beneficiary_fr_dec;
        totalSupply = 0;
    }

    // TODO modifiers
    function destroy(uint _num, address _owner)
        public
    {
        // tokens can not be destroyed until the auction was finalized
        require(auction.finalized());

        StandardToken.destroy(_num, _owner);  // can throw

        uint _value = purchaseCost(_num);
        assert(_value < reserve_value || Utils.xassert(_value, reserve_value, 0, 0));
        _value = SafeMath.min256(_value, reserve_value);
        reserve_value = SafeMath.sub(reserve_value, _value);
        // return _value;
    }

    // TODO return something?
    function create(uint _value, address _recipient)
        public
    {
        if(auction.isAuction()) {
            createDuringAuction(_value, _recipient);
        }
        createGeneral(_value, _recipient);
    }

    function createDuringAuction(uint _value, address _recipient)
        private
    {
        uint rest = auction.missingReserveToEndAuction();
        if(_value > rest) {
            _value = SafeMath.max256(_value, rest);
        }
        reserve_value = SafeMath.add(reserve_value, _value);
        auction.order(_recipient, _value);
        if(auction.finalized()) {
            auction.finalizeAuction();
        }
    }

    function createGeneral(uint _value, address _recipient)
        private
        returns (uint)
    {
        reserve_value = SafeMath.add(reserve_value, _value);
        uint s = supply(reserve_value);
        return issueToken(issued(s, _value), _recipient);
    }

    // TODO override StandardToken.issue
    // TODO modifiers
    function issueToken(uint _num, address _recipient)
        returns (uint)
    {
        // deactivate token.issue until auction has ended
        // during the auction one would call auction.order
        assert(!auction.isAuction());

        // TODO replace beneficiary.fraction
        // uint sold = _num * (1 - beneficiary.fraction);
        // TODO replace this with fraction from supply
        uint sold = SafeMath.sub(_num, beneficiaryFraction(_num));
        uint seigniorage = SafeMath.sub(_num, sold);  // FIXME implement limits

        StandardToken.issue(sold, _recipient);
        StandardToken.issue(seigniorage, beneficiary);
        // TODO: do we need this anymore?
        // reserve_value = SafeMath.add(reserve_value, _value);
        return sold;
    }

    function price(uint _supply)
        constant
        returns (uint)
    {
        if(_supply == 0x0) {
            _supply = totalSupply;
        }
        // TODO factor?
        return SafeMath.add(base_price, priceFactor(_supply));
    }

    function supply(uint _reserve)
        constant
        returns (uint)
    {
        if(_reserve == 0x0) {
            _reserve = reserve_value;
        }
        // TODO factor?
        uint sqrt = Utils.sqrt(
            SafeMath.add(
                base_price**2,
                priceFactor(SafeMath.mul(2, reserve_value))
            ));
        return SafeMath.sub(sqrt, base_price) / priceFactor(1);
    }

    function supplyAtPrice(uint _price)
        constant
        returns (uint)
    {
        // TODO factor?
        return SafeMath.sub(_price, base_price) / priceFactor(1);
    }

    function reserve(uint _supply)
        constant
        returns (uint)
    {
        if(_supply == 0x0) {
            _supply = totalSupply;
        }

        // TODO factor?
        return SafeMath.add(
            SafeMath.mul(base_price, _supply),
            priceFactor(_supply**2) / 2
        );
    }

    function reserveAtPrice(uint _price)
        constant
        returns (uint)
    {
        assert(_price >= 0);
        return reserve(supplyAtPrice(_price));
    }

    // Calculate cost for a number of tokens
    function cost(uint _supply, uint _num)
        constant
        returns (uint)
    {
        return SafeMath.sub(
            reserve(SafeMath.add(_supply, _num)),
            reserve(_supply)
        );
    }

    // Calculate number of tokens issued for a certain value at a certain supply
    function issued(uint _supply, uint _value)
        constant
        returns (uint)
    {
        uint _reserve = reserve(_supply);
        return SafeMath.sub(
            supply(SafeMath.add(_reserve, _value)),
            supply(_reserve)
        );
    }

    function purchaseCost(uint _num)
        constant
        returns (uint)
    {
        // the value offered if tokens are bought back

        if(totalSupply == 0) {
            return 0;
        }

        assert(_num >= 0 && _num <= totalSupply);
        uint c = SafeMath.mul(reserve_value, _num) / totalSupply;
        return c;
    }

    function marketCap(uint _supply)
        constant
        returns (uint)
    {
        return SafeMath.mul(
            price(totalSupply),
            totalSupply
        );
    }

    // TODO
    /*function supplyAtMarketCap(self, m, skipped=0) returns (uint) {
        b, f = self.b, self.f
        f = self.f
        b = (self.b + skipped * self.f)
        s = (-b + sqrt(b**2 - 4 * f * -m)) / (2 * f)
        return s
    }*/

    // We apply this for the supply, in order to lose less when rounding (wei)
    function beneficiaryFraction(uint _supply)
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(_supply, beneficiary_fr) / 10**beneficiary_fr_dec;
    }

    // We apply this for the supply, in order to lose less when rounding (wei)
    function priceFactor(uint _supply)
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(_supply, price_factor) / 10**price_factor_dec;
    }
}
