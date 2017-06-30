pragma solidity ^0.4.11;
import "./utils.sol";


contract Beneficiary {
    using Utils for *;

    // Fraction of all issued tokens
    // This is the source of funding
    uint fraction;
    uint decimals;


    function Beneficiary(uint issuance_fraction, uint _decimals) {
        fraction = issuance_fraction;
        uint dec = Utils.num_digits(int(issuance_fraction));
        if(_decimals == 0x0) {
            decimals = dec;
        }
        else {
            assert(_decimals >= dec);
            decimals = _decimals;
        }
    }

    function get_fraction()  returns(uint value) {
        return fraction;
    }

    function released_fraction() returns(uint value) {
        return 10**decimals - fraction;
    }
}
