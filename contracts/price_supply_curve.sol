pragma solidity ^0.4.11;

import "./utils.sol";
// import "./safe_math.sol";

contract PriceSupplyCurve {
    //using SafeMath for *;
    using Utils for *;

    uint factor;
    uint base_price;

    function PriceSupplyCurve(uint _factor, uint _base_price) {
        factor = _factor;
        base_price = _base_price;
    }

    function bprice() returns(uint value) {
        return base_price;
    }

    function price(uint _supply) returns (uint value) {
        return base_price + factor * _supply;
    }

    function supply(uint _reserve) returns (uint value) {
        return (-base_price + Utils.sqrt(base_price**2 + 2 * factor * _reserve)) / factor;
    }

    function supply_at_price(uint _price) returns (uint value) {
        assert(_price >= base_price);
        return (_price - base_price) / factor;
    }

    function reserve(uint _supply) returns (uint value) {
        return base_price * _supply + factor / 2 * _supply**2;
    }

    function reserve_at_price(uint _price) returns (uint value) {
        assert(_price >= 0);
        return reserve(supply_at_price(_price));
    }

    function cost(uint _supply, uint _num) returns (uint value) {
        return reserve(_supply + _num) - reserve(_supply);
    }

    function issued(uint _supply, uint _value) returns (uint value) {
        uint _reserve = reserve(_supply);
        return supply(_reserve + _value) - supply(_reserve);
    }
}
