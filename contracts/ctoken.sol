pragma solidity ^0.4.11;
import "./token.sol";
import "./auction.sol";
import "./beneficiary.sol";
import "./price_supply_curve.sol";
import "./safe_math.sol";
import "./utils.sol";

contract ContinuousToken {
    using SafeMath for *;
    using Utils for *;

    PriceSupplyCurve curve;
    Auction auction;
    Beneficiary beneficiary;
    Token token = new Token();

    // Amount of currency raised from selling/issuing tokens
    // Cumulated sales price
    uint reserve_value = 0;

    // uint80 constant None = uint80(0);

    function ContinuousToken(PriceSupplyCurve _curve, Beneficiary _beneficiary, Auction _auction) {
        curve = _curve;
        beneficiary = _beneficiary;
        auction = _auction;
    }

    function _notional_supply() returns (uint value) {
        /*
        supply according to reserve_value
        self.token.supply + self._skipped_supply"
        */
        return curve.supply(reserve_value);
    }

    function _skipped_supply() returns (uint value) {
        //tokens that were not issued, due to higher prices during the auction
        assert(token.totalSupply() <= curve.supply(reserve_value));
        return curve.supply(reserve_value) - token.totalSupply();
    }

    function _simulated_supply() returns (uint value) {
        /*
        current auction price converted to additional supply
        note: this is virtual skipped supply,
        so we must not include the skipped supply
        */
        if(auction.price_surcharge() >= curve.bprice()) {
            uint s = curve.supply_at_price(auction.price_surcharge());
            return Utils.max(0, s - _skipped_supply());
        }
        return 0;
    }

    function _arithmetic_supply() returns (uint value) {
        return _notional_supply() + _simulated_supply();
    }

    // cost of selling, purchasing tokens
    function _sale_cost(uint _num) returns (uint value) {
        assert(_num >= 0);
        uint added = _num / (1 - beneficiary.get_fraction());
        return curve.cost(_arithmetic_supply(), added);
    }

    function _purchase_cost_CURVE(uint _num) returns (uint value) {
        // the value offered if tokens are bought back
        assert(_num >= 0 && _num <= token.totalSupply());
        uint c = -curve.cost(_arithmetic_supply(), -_num);
        return c;
    }

    // _purchase_cost_LINEAR
    function _purchase_cost(uint _num) returns (uint value) {
        // the value offered if tokens are bought back
        assert(_num >= 0 && _num <= token.totalSupply());
        uint c = reserve_value * _num / token.totalSupply();
        return c;
    }

    //see how this works in Solidity
    // _purchase_cost = _purchase_cost_LINEAR;

    // Public functions

    function isauction() returns (bool value) {
        return _simulated_supply() > 0;
    }

    function create(uint _value, address _recipient) returns (uint value) {
        // recipient = None (default)

        uint s = _arithmetic_supply();
        uint issued = curve.issued(s, _value);
        uint sold = issued * (1 - beneficiary.get_fraction());
        uint seigniorage = issued - sold;  // FIXME implement limits

        token.issue(sold, _recipient);
        token.issue(seigniorage, beneficiary);
        reserve_value += _value;
        return sold;
    }

    function destroy(uint _num, address _owner) returns (uint value) {
        // _owner=None

        uint _value = _purchase_cost(_num);
        token.destroy(_num, _owner);  // can throw

        assert(_value < reserve_value || Utils.xassert(_value, reserve_value, 0x0, 0x0));
        _value = Utils.min(_value, reserve_value);
        reserve_value -= _value;
        return _value;
    }

    // Public const functions

    function ask() returns (uint value) {
        return _sale_cost(1);
    }

    function bid() returns (uint value) {
        if(reserve_value == 0x0) // ?
            return 0;
        uint bid = _purchase_cost(1);
        assert(bid <= ask());
        return bid;
    }

    function curve_price_auction() returns (uint value) {
        return curve.cost(_arithmetic_supply(), 1);
    }

    function curve_price() returns (uint value) {
        return curve.cost(_notional_supply(), 1);
    }

    function mktcap() returns (uint value) {
        return ask() * token.totalSupply();
    }

    function valuation() returns (uint value) {
        return mktcap() - reserve_value;
    }

    function max_mktcap() returns (uint value) {
        uint vsupply = curve.supply_at_price(ask()) - _skipped_supply();
        return ask() * vsupply;
    }

    function max_valuation() returns (uint value) {
        // FIXME
        return max_mktcap() * beneficiary.get_fraction();
    }

}
