pragma solidity ^0.4.11;

import '../ERC223ReceivingContract.sol';

// Contract needed for testing the token contract
// TODO general function call with 1 data argument in bytes
contract Proxy{

    event Payable(address to, uint value, string function_string);

    function Proxy() {}

    function fund() public payable {}

    function proxy(address to, string func, address data, uint num)
        returns (bool)
    {
        return to.call(bytes4(sha3(func)), data, num);
    }

    function proxyPayable(address to, string function_string)
        payable
        returns (bool)
    {
        Payable(to, msg.value, function_string);
        return to.call.value(msg.value)(bytes4(sha3(function_string)));
    }
}

contract ProxyERC223 is ERC223ReceivingContract{
    address public sender;
    uint256 public value;
    bytes public data;

    function ProxyERC223() {}

    function tokenFallback(
        address _from,
        uint256 _value,
        bytes _data)
        public
    {
        sender = _from;
        value = _value;
        data = _data;
    }


}
