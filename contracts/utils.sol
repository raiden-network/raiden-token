pragma solidity ^0.4.11;

import "./safe_math.sol";

library Utils {
    function num_digits(int number) internal returns (uint) {
        uint digits = 0;
        while (number != 0) {
            number /= 10;
            digits++;
        }
        return digits;
    }

    function validate_fr(uint fraction, uint decimals) internal returns (uint, uint) {
        uint dec = num_digits(int(fraction));
        if(decimals == 0x0) {
            decimals = dec;
        }
        assert(decimals >= dec);
        return (fraction, decimals);
    }

    function fraction_complement(uint fraction, uint decimals) internal returns (uint) {
        return 10**decimals - fraction;
    }

    function abs(int a) returns (uint){
        if (a < 0) {
            return uint(-a);
        }
        return uint(a);
    }

    function sqrt(uint a) internal returns (uint b) {
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

    function xassert(uint a, uint b, uint threshold, uint threshold_dec) internal returns (bool) {
        if(threshold == 0) {
            // default threshold = 0.0001;

            threshold = 1;
            threshold_dec = 4;
        }
        else {
            (threshold, threshold_dec) = validate_fr(threshold, threshold_dec);
        }

        if(SafeMath.min256(a, b) > 0) {
            assert(abs(int(a - b)) / SafeMath.min256(a, b) <= threshold);
        }

        assert(abs(int(a - b)) <= threshold);
        return true;
    }
}
