pragma solidity ^0.4.11;

import './safe_math.sol';

/// @title Abstract token interface - Functions to be implemented by token contracts.
interface Token {
    function balanceOf(address owner) constant returns (uint256 balance);
    function transfer(address to, uint256 value) returns (bool success);
    function transferFrom(address from, address to, uint256 value) returns (bool success);
    //function approve(address spender, uint256 value) returns (bool success);
    //function allowance(address owner, address spender) constant returns (uint256 remaining);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

/// @title Standard token contract - Standard token interface implementation.
contract StandardToken is Token {
    mapping(address => uint) public balances;
    uint public totalSupply;

    /* Events */

    function balanceOf(address _owner)
        constant
        returns (uint)
    {
        return balances[_owner];
    }

    function transfer(address _to, uint _value)
        public
        returns (bool)
    {
        assert(balances[msg.sender] >= _value);
        balances[msg.sender] = SafeMath.sub(balances[msg.sender], _value);
        balances[_to] = SafeMath.add(balances[_to], _value);
        Transfer(msg.sender, _to, _value);
    }

    function transferFrom(address _from, address _to, uint _value)
        public
        returns (bool)
    {
        assert(balances[_from] >= _value);
        balances[_from] = SafeMath.sub(balances[_from], _value);
        balances[_to] = SafeMath.add(balances[_to], _value);
        Transfer(msg.sender, _to, _value);
    }
}
