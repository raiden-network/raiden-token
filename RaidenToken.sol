pragma solidity 0.4.11;
import "token.sol";

/// @title Raiden token contract
/// @author Heiko Hees

contract RaidenToken is StandardToken {

    /*  Token meta data */

    string constant public name = "Raiden Token";
    string constant public symbol = "RDN";
    uint constant public decimals = 24;  // ETH has 18
    uint public maxSupply = 10 * 1000000 * 10**decimals; // TODO should be constant?
    address public mint;

    /* Events */

    event Minted(address indexed receiver, uint num, uint _totalSupply);
    event Destroyed(address indexed receiver, uint num, uint _totalSupply);
    event CollateralUpdated(uint changed, uint newETHValue);

    /*  Public functions */

    /// @dev Contract constructor function sets the mint contract address
    /// @param _mint Address of dutch auction contract.
    /// @param owners Array of addresses receiving preassigned tokens.
    /// @param numtokens Array of preassigned token amounts.
    function RaidenToken(address _mint, address[] owners, uint[] numtokens) public {
        // prealloc tokens
        for (uint i = 0; i < owners.length; i++) {
            require(owners[i] != 0x0);
            mint(owners[i], numtokens[i]);
        }
        assert(totalSupply <= maxSupply);

        // assign mint
        mint = _mint;
    }

    function mint(address receiver, uint num) public returns (bool) {
        require(msg.sender == address(this) || msg.sender == mint);

        totalSupply += num;
        assert(totalSupply <= maxSupply);

        balances[receiver] += num;
        Transfer(0, receiver, num);

        Minted(receiver, num, totalSupply);
        return true;
    }

    // used to safely send ETH to the contract
    // FIXME: default function should fail, right?
    function addCollateral() public payable returns (bool) {
        require(msg.sender == mint); // FIXME: required restriction?

        CollateralUpdated(msg.value, this.balance);
        return true;
    }

    function tokensPerWei() public constant returns (uint) {
        return totalSupply / this.balance; // wei per token FIXME
    }

    function destroy(uint num) public returns (bool) {
        require(balances[msg.sender] >= num);

        uint unlockedETH = num / tokensPerWei();
        uint pre = this.balance;

        balances[msg.sender] -= num;
        totalSupply -= num;
        maxSupply -= num; // TODO should this happen? Or is this value constant?

        // transfer unlocked ETH back to msg.sender
        msg.sender.transfer(unlockedETH);

        require(this.balance == pre - unlockedETH);

        Destroyed(msg.sender, num, totalSupply);
        CollateralUpdated(-unlockedETH, this.balance);
        // TODO: maybe have separate event for increase and decrease collateral?

        return true;
    }
}
