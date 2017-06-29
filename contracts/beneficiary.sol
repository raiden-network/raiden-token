pragma solidity ^0.4.2;

contract Beneficiary {
    // Fraction of all issued tokens
    // This is the source of funding
    uint256 fraction;

    function Beneficiary(uint256 issuance_fraction) {
        fraction = issuance_fraction;
    }

    function get_fraction()  returns(uint256 value) {
        return fraction;
    }
}
