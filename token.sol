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
    string constant public symbol = "RDB";
    uint8 constant public decimals = 24;  // ETH has 18
    uint constant public maxSupply = 10 * 1000000 * 10**decimals;
    address public mint;

    event Minted(address indexed receiver, uint num, uint _totalSupply);
    event Destroyed(address indexed receiver, uint num, uint _totalSupply);
    event CollateralChanged(int changed, uint newETHValue);


    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets the mint contract address
    /// @param mint Address of dutch auction contract.
    /// @param owners Array of addresses receiving preassigned tokens.
    /// @param numtokens Array of preassigned token amounts.
    function RaidenToken(address mint; address[] owners, uint[] numtokens)
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
        assert(msg.sender == this.address || msg.sender == mint);
        totalSupply += num;
        assert(totalSupply <= maxSupply);
        balances[receiver] += num;
        Transfer(0, receiver, num);
        Minted(receiver, num, totalSupply);
        return true;
    }


    // used to safely send ETH to the contract
    // FIXME default function should fail
    function addCollateral()
        public
        payable
        returns (bool)
    {
        assert(msg.sender == mint); // FIXME: required restriction? also the auction is collecting it
        CollateralUpdated(msg.value, this.value);
        return true;
    }


    function tokensPerWei()
        public
        constant
        returns (uint)
    {
        return totalSupply / this.value; // wei per token FIXME
    }


    function destroy(num)
        public
        returns (uint)
    {
        assert(balance[msg.sender] >= num);
        balance[msg.sender] -= num;
        unlockedETH = num / tokensPerWei();
        assert(send(msg.sender, unlockedETH));
        Destroyed(msg.sender, num, totalSupply);
        CollateralUpdated(-unlockedETH, this.value);
        return true;
    }


}
