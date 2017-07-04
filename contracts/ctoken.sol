pragma solidity ^0.4.11;

import './safe_math.sol';
import './utils.sol';
import './token.sol';
import './mint.sol';

contract ContinuousToken is StandardToken {

    string constant public name = 'Continuous Token';
    string constant public symbol = '';
    uint8 constant public decimals = 24;

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

    event Issued(address indexed receiver, uint num, uint _totalSupply);
    event Destroyed(address indexed receiver, uint num, uint _totalSupply);
    event LogMintFundsReceived(uint value, uint balance);

    function ContinuousToken(address _mint)
    {
        owner = msg.sender;
        mint = Mint(_mint);
        totalSupply = 0;
    }

    function issue(address _recipient, uint _num)
        public
        isMint
    {
        if(balances[_recipient] != 0x0) {
            balances[_recipient] = 0;
        }
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
