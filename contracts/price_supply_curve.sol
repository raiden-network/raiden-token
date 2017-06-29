pragma solidity ^0.4.2;

contract PriceSupplyCurve {
    uint256 factor;
    uint256 base_price;

    function PriceSupplyCurve(uint256 _factor, uint256 _base_price) {
        factor = _factor;
        base_price = _base_price;
    }

    function base_p() returns(uint256 value) {
        return base_price;
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
        assert(_price >= base_price);
        return (_price - base_price) / factor;
    }

    function reserve(uint256 _supply) returns (uint256 value) {
        return base_price * _supply + factor / 2 * _supply**2;
    }

    function reserve_at_price(uint256 _price) returns (uint256 value) {
        assert(_price >= 0);
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
