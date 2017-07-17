pragma solidity ^0.4.11;

// Contract needed for testing
// TODO general function call with 1 data argument in bytes
contract Proxy {

    event Payable(address to, uint value, string function_string);
    function Proxy() {}

    function proxy(address to, string func, address data, uint num)
        returns (bool)
    {
        return to.call(bytes4(sha3(func)), data, num);
    }

    function proxyPayable(address to, string function_string, uint value)
        payable
        returns (bool)
    {
        Payable(to, value, function_string);
        return to.call.value(value)(bytes4(sha3(function_string)));
    }
}
