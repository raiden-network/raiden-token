pragma solidity ^0.4.2;

contract Token {

    uint256 supply = 0;
    mapping(address => uint256) public accounts;

    function Token() {}

    // ERC20

    function totalSupply() constant returns (uint256 supply) {
        return supply;
    }

    function balanceOf(address _owner) constant returns (uint256 balance) {
        return accounts[_owner];
    }

    function transfer(address _to, uint256 _value) returns (bool success) {
        assert(accounts[msg.sender] >= _value);
        accounts[msg.sender] -= _value;
        accounts[_to] += _value;
    }

    function transferFrom(address _from, address _to, uint256 _value) returns (bool success) {
        assert(accounts[_from] >= _value);
        accounts[_from] -= _value;
        accounts[_to] += _value;
    }

    //function approve(address _spender, uint256 _value) returns (bool success);
    //function allowance(address _owner, address _spender) returns (uint256 value);

    event Transfer(address indexed _from, address indexed _to, uint256 _value);
    event Approval(address indexed _owner, address indexed _spender, uint256 _value);

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
