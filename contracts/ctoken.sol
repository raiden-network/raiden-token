pragma solidity ^0.4.11;

import './safe_math.sol';
import './token.sol';
import './mint.sol';

contract ContinuousToken is StandardToken {

    string constant public name = 'Continuous Token';
    string constant public symbol = '';
    uint8 constant public decimals = 18;

    Mint mint;
    address public owner;

    modifier isOwner() {
        require(msg.sender == owner);
        _;
    }

    modifier isMint() {
        require(msg.sender == address(mint));
        _;
    }

    event Deployed(address indexed _token);
    event Issued(address indexed receiver, uint num, uint _totalSupply);
    event Destroyed(address indexed receiver, uint num, uint _totalSupply);

    function ContinuousToken(address _mint)
    {
        owner = msg.sender;
        mint = Mint(_mint);
        Deployed(this);
    }

    function issue(address _recipient, uint _num)
        public
        isMint
    {
        balances[_recipient] = SafeMath.add(balances[_recipient], _num);
        totalSupply = SafeMath.add(totalSupply, _num);
        Issued(_recipient, _num, totalSupply);
    }

    function destroy(address _owner, uint _num)
        public
        isMint
    {
        assert(balances[_owner] >= _num);
        balances[_owner] = SafeMath.sub(balances[_owner], _num);
        totalSupply = SafeMath.sub(totalSupply, _num);
        Destroyed(_owner, _num, totalSupply);
    }
}
