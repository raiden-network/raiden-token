pragma solidity 0.4.11;


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

    /*
     *  Data structures
     */
    mapping (address => uint256) balances;
    mapping (address => mapping (address => uint256)) allowed;
    uint256 public totalSupply;

    /*
     *  Public functions
     */
    /// @dev Transfers sender's tokens to a given address. Returns success.
    /// @param _to Address of token receiver.
    /// @param _value Number of tokens to transfer.
    /// @return Returns success of function call.
    function transfer(address _to, uint256 _value)
        public
        returns (bool)
    {
        if (balances[msg.sender] < _value) {
            // Balance too low
            throw;
        }
        balances[msg.sender] -= _value;
        balances[_to] += _value;
        Transfer(msg.sender, _to, _value);
        return true;
    }

    /// @dev Allows allowed third party to transfer tokens from one address to another. Returns success.
    /// @param _from Address from where tokens are withdrawn.
    /// @param _to Address to where tokens are sent.
    /// @param _value Number of tokens to transfer.
    /// @return Returns success of function call.
    function transferFrom(address _from, address _to, uint256 _value)
        public
        returns (bool)
    {
        if (balances[_from] < _value || allowed[_from][msg.sender] < _value) {
            // Balance or allowance too low
            throw;
        }
        balances[_to] += _value;
        balances[_from] -= _value;
        allowed[_from][msg.sender] -= _value;
        Transfer(_from, _to, _value);
        return true;
    }

    /// @dev Sets approved amount of tokens for spender. Returns success.
    /// @param _spender Address of allowed account.
    /// @param _value Number of approved tokens.
    /// @return Returns success of function call.
    function approve(address _spender, uint256 _value)
        public
        returns (bool)
    {
        allowed[msg.sender][_spender] = _value;
        Approval(msg.sender, _spender, _value);
        return true;
    }

    /*
     * Read functions
     */
    /// @dev Returns number of allowed tokens for given address.
    /// @param _owner Address of token owner.
    /// @param _spender Address of token spender.
    /// @return Returns remaining allowance for spender.
    function allowance(address _owner, address _spender)
        constant
        public
        returns (uint256)
    {
        return allowed[_owner][_spender];
    }

    /// @dev Returns number of tokens owned by given address.
    /// @param _owner Address of token owner.
    /// @return Returns balance of owner.
    function balanceOf(address _owner)
        constant
        public
        returns (uint256)
    {
        return balances[_owner];
    }
}


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
