pragma solidity ^0.4.11;

contract Token {

    uint supply = 0;
    mapping(address => uint) public accounts;

    function Token() {}

    // ERC20

    function totalSupply() constant returns (uint supply) {
        return supply;
    }

    function balanceOf(address _owner) constant returns (uint balance) {
        return accounts[_owner];
    }

    function transfer(address _to, uint _value) returns (bool success) {
        assert(accounts[msg.sender] >= _value);
        accounts[msg.sender] -= _value;
        accounts[_to] += _value;
    }

    function transferFrom(address _from, address _to, uint _value) returns (bool success) {
        assert(accounts[_from] >= _value);
        accounts[_from] -= _value;
        accounts[_to] += _value;
    }

    //function approve(address _spender, uint _value) returns (bool success);
    //function allowance(address _owner, address _spender) returns (uint value);

    event Transfer(address indexed _from, address indexed _to, uint _value);
    event Approval(address indexed _owner, address indexed _spender, uint _value);

    // Custom functions
    function issue(uint _num, address _recipient) {
        if(accounts[_recipient] != 0x0)
            accounts[_recipient] = 0;
        accounts[_recipient] += _num;
        supply += _num;
    }

	function destroy(uint _num, address _owner) {
        // InsufficientFundsError
        if(accounts[_owner] < _num)
            throw;

        accounts[_owner] -= _num;
        supply -= _num;
	}

}
