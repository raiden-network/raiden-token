pragma solidity ^0.4.11;

import '../ERC223ReceivingContract.sol';
import '../token.sol';

/// @title Custom Token
contract CustomToken2 is StandardToken {

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
    uint8 public decimals;
    uint multiplier;

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
    function CustomToken2(
        uint8 _decimals,
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
        decimals = _decimals;
        multiplier = 10**uint(decimals);

        // Total supply of Tei at deployment
        totalSupply = initial_supply;

        // Preallocate tokens to beneficiaries
        uint prealloc_tokens;
        for (uint i = 0; i < owners.length; i++) {
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

        assert(balances[auction_address] > 0);
        assert(balances[auction_address] < totalSupply);
        assert(totalSupply == balances[auction_address] + prealloc_tokens);
    }

    /// @notice Allows `msg.sender` to simply destroy `num` token units (Tei),
    /// without receiving the corresponding amount of ether. This means the total
    /// token supply will decrease.
    /// @dev Allows to destroy token units (Tei) without receiving the
    /// corresponding amount of ether.
    /// @param num Number of token units (Tei) to burn.
    function burn(uint num) public {
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
