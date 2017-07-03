pragma solidity ^0.4.11;

import "./safe_math.sol";

/// @title Abstract token contract - Functions to be implemented by token contracts.
contract Token {
    function transfer(address to, uint256 value) returns (bool success);
    function transferFrom(address from, address to, uint256 value) returns (bool success);
    function approve(address spender, uint256 value) returns (bool success);

    // This is not an abstract function, because solc won't recognize generated getter functions for public variables as functions.
    function totalSupply() constant returns (uint256 supply) {}
    function balanceOf(address owner) constant returns (uint256 balance);
    function allowance(address owner, address spender) constant returns (uint256 remaining);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

/// @title Standard token contract - Standard token interface implementation.
contract StandardToken is Token {
    mapping(address => uint) public balances;
    uint public totalSupply;

    /* Events */

    event Issued(address indexed receiver, uint num, uint _totalSupply);
    event Destroyed(address indexed receiver, uint num, uint _totalSupply);

    function balanceOf(address _owner) constant returns (uint) {
        return balances[_owner];
    }

    function transfer(address _to, uint _value) public returns (bool) {
        assert(balances[msg.sender] >= _value);
        balances[msg.sender] = SafeMath.sub(balances[msg.sender], _value);
        balances[_to] = SafeMath.add(balances[_to], _value);
    }

    function transferFrom(address _from, address _to, uint _value) public returns (bool) {
        assert(balances[_from] >= _value);
        balances[_from] = SafeMath.sub(balances[_from], _value);
        balances[_to] = SafeMath.add(balances[_to], _value);
    }

    function issue(uint _num, address _recipient) public {
        if(balances[_recipient] != 0x0)
            balances[_recipient] = 0;
        balances[_recipient] = SafeMath.add(balances[_recipient], _num);
        totalSupply = SafeMath.add(totalSupply, _num);
        Issued(_recipient, _num, totalSupply);
    }

	function destroy(uint _num, address _owner) {
        assert(balances[_owner] >= _num);
        balances[_owner] = SafeMath.sub(balances[_owner], _num);
        totalSupply = SafeMath.sub(totalSupply, _num);
        Destroyed(_owner, _num, totalSupply);
	}
}
