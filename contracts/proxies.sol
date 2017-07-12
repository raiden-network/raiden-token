pragma solidity ^0.4.11;

import './mint.sol';

// Contract needed for testing
// TODO general function call with 1 data argument in bytes
contract MintProxy {
    function MintProxy() {}

    function proxy(address to, string func, address data, uint num)
        returns (bool)
    {
        return to.call(bytes4(sha3(func)), data, num);
    }
}
