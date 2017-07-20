pragma solidity ^0.4.11;

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
        require(balances[msg.sender] >= _value);

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
        require(balances[_from] >= _value);
        require(allowed[_from][msg.sender] >= _value);

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


/// @title Gnosis token contract
/// @author [..] credits to Stefan George - <stefan.george@consensys.net>
contract RaidenToken is StandardToken {

    /*
     *  Token meta data
     */
    string constant public name = "Raiden Token";
    string constant public symbol = "RDN";
    uint8 constant public decimals = 18;
    uint constant multiplier = 10**18;

    address auction_address;

    event Redeemed(address indexed receiver, uint num, uint unlocked, uint _totalSupply);
    event ReceivedReserve(uint num);

    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets dutch auction contract address and assigns all tokens to dutch auction.
    /// @param auction Address of dutch auction contract.
    /// @param owners Array of addresses receiving preassigned tokens.
    /// @param tokens Array of preassigned token amounts.
    function RaidenToken(address auction, address[] owners, uint[] tokens)
        public
    {
        // Auction address should not be null.
        require(auction != 0x0);

        auction_address = auction;
        totalSupply = 10000000 * multiplier;
        balances[auction] = 9000000 * multiplier;
        Transfer(0, auction, balances[auction]);
        uint assignedTokens = balances[auction];

        for (uint i=0; i<owners.length; i++) {
            // Address should not be null.
            require(owners[i] != 0x0);

            balances[owners[i]] += tokens[i];
            Transfer(0, owners[i], tokens[i]);
            assignedTokens += tokens[i];
        }
        assert(assignedTokens == totalSupply);
    }

    /// @dev called from auction after it has ended to transfer the reserve
    function receiveReserve()
        public
        payable
    {
        require(msg.sender == auction_address);
        ReceivedReserve(msg.value);
    }

    /// @dev allows to destroy tokens and receive the corresponding amount of ether, implements the floor price
    function redeem(uint num)
        public
    {
        require(num > 0);
        assert(balances[msg.sender] >= num);
        assert(this.balance > 0);

        balances[msg.sender] -= num;
        uint unlocked = this.balance * num / totalSupply;
        Redeemed(msg.sender, msg.sender.balance, unlocked, totalSupply);
        totalSupply -= num;
        msg.sender.transfer(unlocked);
        Redeemed(msg.sender, num, unlocked, totalSupply);
    }

}
