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
        require(_to != 0x0);
        require(_value > 0);
        require(balances[msg.sender] >= _value);
        require(balances[_to] + _value > balances[_to]);

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
        require(_from != 0x0);
        require(_to != 0x0);
        require(_value > 0);
        require(balances[_from] >= _value);
        require(allowed[_from][_to] >= _value);
        require(balances[_to] + _value > balances[_to]);

        balances[_to] += _value;
        balances[_from] -= _value;
        allowed[_from][_to] -= _value;
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
        require(_spender != 0x0);
        require(_value > 0);

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
contract ReserveToken is StandardToken {

    /*
     *  Token meta data
     */
    string constant public name = "The Token";
    string constant public symbol = "TKN";
    uint8 constant public decimals = 18;
    uint constant multiplier = 10**uint(decimals);

    address public owner;
    address public auction_address;

    event Deployed(address indexed auction, uint indexed initial_supply, uint indexed auction_supply);
    event Redeemed(address indexed receiver, uint num, uint unlocked, uint _totalSupply);
    event Burnt(address indexed receiver, uint num, uint _totalSupply);
    event ReceivedReserve(uint num);

    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets dutch auction contract address and assigns all tokens to dutch auction.
    /// @param auction Address of dutch auction contract.
    /// @param initial_supply Number of initially provided tokens.
    /// @param owners Array of addresses receiving preassigned tokens.
    /// @param tokens Array of preassigned token amounts.
    function ReserveToken(address auction, uint initial_supply, address[] owners, uint[] tokens)
        public
    {
        // Auction address should not be null.
        require(auction != 0x0);
        require(owners.length == tokens.length);
        // Initial supply is in Tei
        require(initial_supply > multiplier);

        owner = msg.sender;
        auction_address = auction;

        // total supply of Tei at deployment
        totalSupply = initial_supply;

        // Preallocate tokens to beneficiaries
        uint prealloc_tokens;
        for (uint i=0; i<owners.length; i++) {
            // Address should not be null.
            require(owners[i] != 0x0);
            require(tokens[i] > 0);
            require(balances[owners[i]] + tokens[i] > balances[owners[i]]);
            require(prealloc_tokens + tokens[i] > prealloc_tokens);

            balances[owners[i]] += tokens[i];
            prealloc_tokens += tokens[i];
            Transfer(0, owners[i], tokens[i]);
        }

        balances[auction_address] = totalSupply - prealloc_tokens;
        Transfer(0, auction_address, balances[auction]);

        Deployed(auction_address, totalSupply, balances[auction]);

        assert(totalSupply == balances[auction_address] + prealloc_tokens);
    }

    /// @dev Transfers auction's reserve; called from auction after it has ended.
    function receiveReserve()
        public
        payable
    {
        require(msg.sender == auction_address);
        require(msg.value > 0);

        ReceivedReserve(msg.value);
        assert(this.balance > 0);
    }

    /// @dev Allows to destroy tokens and receive the corresponding amount of ether, implements the floor price
    /// @param num Number of tokens to redeem
    function redeem(uint num)
        public
    {
        require(num > 0);
        require(this.balance > 0);

        // Calculate amount of Wei to be transferred to sender before burning
        uint unlocked = this.balance * num / totalSupply;

        // Burn tokens before Wei transfer
        burn(num);

        uint pre_balance = this.balance;

        // Transfer Wei to sender
        msg.sender.transfer(unlocked);
        Redeemed(msg.sender, num, unlocked, totalSupply);

        assert(unlocked > 0);
        assert(this.balance == pre_balance - unlocked);

        // TODO remove after testing
        assert(num == (unlocked * totalSupply / this.balance));
    }

    /// @dev Allows to destroy tokens without receiving the corresponding amount of ether
    /// @param num Number of tokens to burn
    function burn(uint num)
        public
    {
        require(num > 0);
        require(balances[msg.sender] >= num);
        require(totalSupply >= num);

        uint pre_balance = balances[msg.sender];

        balances[msg.sender] -= num;
        totalSupply -= num;
        Burnt(msg.sender, num, totalSupply);

        assert(balances[msg.sender] == pre_balance - num);
    }

}
