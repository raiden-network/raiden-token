pragma solidity ^0.4.11;

import "./safe_math.sol";

library Utils {
    using SafeMath for *;

    function min(uint a, uint b) returns (uint) {
        return SafeMath.min256(a, b);
    }

    function max(uint a, uint b) returns (uint) {
        return SafeMath.max256(a, b);
    }

    function num_digits(int number) internal returns (uint) {
        uint digits = 0;
        while (number != 0) {
            number /= 10;
            digits++;
        }
        return digits;
    }

    function validate_fr(uint fraction, uint decimals) returns (uint, uint) {
        uint dec = num_digits(int(fraction));
        if(decimals == 0x0) {
            decimals = dec;
        }
        assert(decimals >= dec);
        return (fraction, decimals);
    }

    function fraction_complement(uint fraction, uint decimals) returns (uint) {
        return 10**decimals - fraction;
    }

    function abs(int a) returns (uint){
        if (a < 0) {
            return uint(-a);
        }
        return uint(a);
    }

    function sqrt(uint a) returns (uint b) {
        if (a == 0)
            return 0;
        else if (a <= 3)
            return 1;

        uint z = (a + 1) / 2;
        b = a;
        while (z < b) {
            b = z;
            z = (a / z + z) / 2;
        }
    }

    function xassert(uint a, uint b, uint threshold, uint threshold_dec) returns (bool) {
        if(threshold == 0x0) {
            // default threshold = 0.0001;

            threshold = 1;
            threshold_dec = 4;
        }
        else {
            (threshold, threshold_dec) = validate_fr(threshold, threshold_dec);
        }

        if(min(a, b) > 0) {
            assert(abs(int(a - b)) / min(a, b) <= threshold);
        }

        assert(abs(int(a - b)) <= threshold);
        return true;
    }
}
