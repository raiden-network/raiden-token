pragma solidity ^0.4.2;
import "./token.sol";
import "./auction.sol";
import "./beneficiary.sol";
import "./price_supply_curve.sol";

contract ContinuousToken {
    PriceSupplyCurve curve;
    Auction auction;
    Beneficiary beneficiary;
    Token token = new Token();

    // Amount of currency raised from selling/issuing tokens
    // Cumulated sales price
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
    function xassert(uint256 _a, uint256 _b) returns (bool almost_equal) {
        // threshold = 0.0001;
        // uint256 threshold

        if(min(_a, _b) > 0) {
            //assert(abs(a - b) / min(a, b) <= threshold, (a, b));
        }

        // assert(abs(a - b) <= threshold, (a, b));
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
        assert(token.totalSupply() <= curve.supply(reserve_value));
        return curve.supply(reserve_value) - token.totalSupply();
    }

    function _simulated_supply() returns (uint256 value) {
        /*
        current auction price converted to additional supply
        note: this is virtual skipped supply,
        so we must not include the skipped supply
        */
        if(auction.price_surcharge() >= curve.base_p()) {
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
        assert(_num >= 0);
        uint256 added = _num / (1 - beneficiary.get_fraction());
        return curve.cost(_arithmetic_supply(), added);
    }

    function _purchase_cost_CURVE(uint256 _num) returns (uint256 value) {
        // the value offered if tokens are bought back
        assert(_num >= 0 && _num <= token.totalSupply());
        uint256 c = -curve.cost(_arithmetic_supply(), -_num);
        return c;
    }

    // _purchase_cost_LINEAR
    function _purchase_cost(uint256 _num) returns (uint256 value) {
        // the value offered if tokens are bought back
        assert(_num >= 0 && _num <= token.totalSupply());
        uint256 c = reserve_value * _num / token.totalSupply();
        return c;
    }

    //see how this works in Solidity
    // _purchase_cost = _purchase_cost_LINEAR;

    // Public functions

    function isauction() returns (bool value) {
        return _simulated_supply() > 0;
    }

    function create(uint256 _value, address _recipient) returns (uint256 value) {
        // recipient = None (default)

        uint256 s = _arithmetic_supply();
        uint256 issued = curve.issued(s, _value);
        uint256 sold = issued * (1 - beneficiary.get_fraction());
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

        assert(_value < reserve_value || xassert(_value, reserve_value));
        _value = min(_value, reserve_value);
        reserve_value -= _value;
        return _value;
    }

    // Public const functions

    function ask() returns (uint256 value) {
        return _sale_cost(1);
    }

    function bid() returns (uint256 value) {
        if(reserve_value == 0x0) // ?
            return 0;
        uint256 bid = _purchase_cost(1);
        assert(bid <= ask());
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
        return mktcap() - reserve_value;
    }

    function max_mktcap() returns (uint256 value) {
        uint256 vsupply = curve.supply_at_price(ask()) - _skipped_supply();
        return ask() * vsupply;
    }

    function max_valuation() returns (uint256 value) {
        // FIXME
        return max_mktcap() * beneficiary.get_fraction();
    }

}
