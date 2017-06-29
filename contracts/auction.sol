pragma solidity ^0.4.2;

contract Auction {
    uint256 factor;
    uint256 const;
    uint256 elapsed = 0;

    function Auction(uint256 _factor, uint256 _const) {
        factor = _factor;
        _const = const;
    }

    // Simulated supply
    function price_surcharge() returns(uint256 value) {
        return factor / elapsed + const;
    }
}
