pragma solidity ^0.4.11;

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
}
