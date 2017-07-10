pragma solidity ^0.4.11;

import "./safe_math.sol";

library Utils {
    function num_digits(uint number)
        internal
        constant
        returns (uint)
    {
        uint digits = 0;
        while (number != 0) {
            number /= 10;
            digits++;
        }
        return digits;
    }

    function abs(int a)
        internal
        constant
        returns (uint)
    {
        if (a < 0) {
            return uint(-a);
        }
        return uint(a);
    }

    function sqrt(uint a)
        internal
        constant
        returns (uint b)
    {
        if (a == 0) {
            return 0;
        }
        else if (a <= 3) {
            return 1;
        }

        uint z = SafeMath.add(a, 1) / 2;
        b = a;
        while (z < b) {
            b = z;
            z = SafeMath.add(a / z, z) / 2;
        }
    }
}
