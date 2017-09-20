pragma solidity ^0.4.11;

import './ERC223ReceivingContract.sol';

/// @title Base Token contract - Functions to be implemented by token contracts.
contract Token {
    /*
        Implements ERC 20 standard.
        https://github.com/ethereum/EIPs/blob/f90864a3d2b2b45c4decf95efd26b3f0c276051a/EIPS/eip-20-token-standard.md
        https://github.com/ethereum/EIPs/issues/20

        Added support for the ERC 223 "tokenFallback" method in a "transfer" function with a payload.
        https://github.com/ethereum/EIPs/issues/223
     */

    /*
        This is a slight change to the ERC20 base standard.
        function totalSupply() constant returns (uint256 supply);
        is replaced with:
        uint256 public totalSupply;
        This automatically creates a getter function for the totalSupply.
        This is moved to the base contract since public getter functions are not
        currently recognised as an implementation of the matching abstract
        function by the compiler.
    */
    uint256 public totalSupply;

    /*
     *  ERC 20
     */
    function balanceOf(address _owner) constant returns (uint256 balance);
    function transfer(address _to, uint256 _value) returns (bool success);
    function transferFrom(address _from, address _to, uint256 _value) returns (bool success);
    function approve(address _spender, uint256 _value) returns (bool success);
    function allowance(address _owner, address _spender) constant returns (uint256 remaining);

    /*
     *  ERC 223
     */
    function transfer(address _to, uint256 _value, bytes _data) returns (bool success);

    /*
     *  Events
     */
    event Transfer(
        address indexed _from,
        address indexed _to,
        uint256 _value);
    event Approval(
        address indexed _owner,
        address indexed _spender,
        uint256 _value);
}


/// @title Standard token contract - Standard token implementation.
contract StandardToken is Token {

    /*
     *  Data structures
     */
    mapping (address => uint256) balances;
    mapping (address => mapping (address => uint256)) allowed;

    /*
     *  Public functions
     */
    /// @notice Send `_value` tokens to `_to` from `msg.sender`.
    /// @dev Transfers sender's tokens to a given address. Returns success.
    /// @param _to Address of token receiver.
    /// @param _value Number of tokens to transfer.
    /// @return Returns success of function call.
    function transfer(address _to, uint256 _value)
        public
        returns (bool)
    {
        require(_to != 0x0);
        require(balances[msg.sender] >= _value);
        require(balances[_to] + _value >= balances[_to]);

        balances[msg.sender] -= _value;
        balances[_to] += _value;

        Transfer(msg.sender, _to, _value);

        return true;
    }

    /// @notice Send `_value` tokens to `_to` from `msg.sender` and trigger tokenFallback if sender is a contract.
    /// @dev Function that is called when a user or another contract wants to transfer funds.
    /// @param _to Address of token receiver.
    /// @param _value Number of tokens to transfer.
    /// @param _data Data to be sent to tokenFallback
    /// @return Returns success of function call.
    function transfer(
        address _to,
        uint256 _value,
        bytes _data)
        public
        returns (bool)
    {
        assert(transfer(_to, _value));

        uint codeLength;

        assembly {
            // Retrieve the size of the code on target address, this needs assembly .
            codeLength := extcodesize(_to)
        }

        if(codeLength > 0) {
            ERC223ReceivingContract receiver = ERC223ReceivingContract(_to);
            receiver.tokenFallback(msg.sender, _value, _data);
        }

        return true;
    }

    /// @notice Transfer `_value` tokens from `_from` to `_to` if `msg.sender` is allowed.
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
        require(balances[_from] >= _value);
        require(allowed[_from][msg.sender] >= _value);
        require(balances[_to] + _value >= balances[_to]);

        balances[_to] += _value;
        balances[_from] -= _value;
        allowed[_from][msg.sender] -= _value;

        Transfer(_from, _to, _value);

        return true;
    }

    /// @notice Allows `_spender` to transfer `_value` tokens from `msg.sender` to any address.
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
    /// @dev Returns number of allowed tokens that a spender can transfer in behalf of a token owner.
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

    /// @dev Returns number of tokens owned by the given address.
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


/// @title Custom Token
contract CustomToken is StandardToken {

    /*
     *  Terminology:
     *  1 token unit = Tei
     *  1 token = TKN = Tei * multiplier
     *  multiplier set from token's number of decimals (i.e. 10**decimals)
     */

    /*
     *  Token metadata
     */
    string constant public name = "The Token";
    string constant public symbol = "TKN";
    uint8 constant public decimals = 18;
    uint constant multiplier = 10**uint(decimals);

    address public owner;
    address public auction_address;

    event Deployed(
        address indexed _auction,
        uint indexed _total_supply,
        uint indexed _auction_supply);
    event Burnt(
        address indexed _receiver,
        uint indexed _num,
        uint indexed _total_supply);

    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets dutch auction contract address and assigns all tokens to dutch auction.
    /// @param auction Address of dutch auction contract.
    /// @param initial_supply Number of initially provided token units (Tei).
    /// @param owners Array of addresses receiving preassigned tokens.
    /// @param tokens Array of preassigned token units (Tei).
    function CustomToken(
        address auction,
        uint initial_supply,
        address[] owners,
        uint[] tokens)
        public
    {
        // Auction address should not be null.
        require(auction != 0x0);
        require(owners.length == tokens.length);
        // Initial supply is in Tei
        require(initial_supply > multiplier);

        owner = msg.sender;
        auction_address = auction;

        // Total supply of Tei at deployment
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

    /// @notice Allows `msg.sender` to simply destroy `num` token units (Tei), without receiving the corresponding amount of ether. This means the total token supply will decrease.
    /// @dev Allows to destroy token units (Tei) without receiving the corresponding amount of ether.
    /// @param num Number of token units (Tei) to burn.
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
