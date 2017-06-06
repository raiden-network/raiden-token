pragma solidity 0.4.11;
import "token.sol";

/// @title Raiden token contract
/// @author Heiko Hees

contract RaidenToken is StandardToken {

    /*
     *  Token meta data
     */
    string constant public name = "Raiden Token";
    string constant public symbol = "RDN";
    uint constant public decimals = 24;  // ETH has 18
    uint public maxSupply = 10 * 1000000 * 10**decimals;
    address public minter;

    event Minted(address indexed receiver, uint num, uint _totalSupply);
    event Destroyed(address indexed receiver, uint num, uint _totalSupply);
    event CollateralUpdated(uint changed, uint newETHValue);

    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets the mint contract address
    /// @param mint Address of dutch auction contract.
    /// @param owners Array of addresses receiving preassigned tokens.
    /// @param numtokens Array of preassigned token amounts.
    function RaidenToken(address minter, address[] owners, uint[] numtokens)
        public
    {
        // prealloc
        for (uint i=0; i<owners.length; i++) {
            assert(owners[i] != 0);
            mint(owners[i], numtokens[i]);
        }
        assert(totalSupply <= maxSupply);
    }

    function mint(address receiver, uint num)
        public
        returns (bool)
    {
        assert(msg.sender == address(this) || msg.sender == minter);
        totalSupply += num;
        assert(totalSupply <= maxSupply);
        balances[receiver] += num;
        Transfer(0, receiver, num);
        Minted(receiver, num, totalSupply);
        return true;
    }

    // used to safely send ETH to the contract
    // FIXME: default function should fail, right?
    function addCollateral()
        public
        payable
        returns (bool)
    {
        assert(msg.sender == minter); // FIXME: required restriction?
        CollateralUpdated(msg.value, this.balance);
        return true;
    }

    function tokensPerWei()
        public
        constant
        returns (uint)
    {
        return totalSupply / this.balance; // wei per token FIXME
    }

    function destroy(uint num)
        public
        returns (bool)
    {
        assert(balances[msg.sender] >= num);
        balances[msg.sender] -= num;
        totalSupply -= num;
        maxSupply -= num;
        uint unlockedETH = num / tokensPerWei();
        uint pre = this.balance;
        msg.sender.transfer(unlockedETH);
        assert(this.balance == pre - unlockedETH);
        Destroyed(msg.sender, num, totalSupply);
        CollateralUpdated(-unlockedETH, this.balance);
        return true;
    }
}
