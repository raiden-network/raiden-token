pragma solidity ^0.4.11;

import './auction.sol';

/// @title Distributor contract - distribution of tokens after an auction has ended.
contract Distributor {
    /*
     * Storage
     */

    DutchAuction public auction;

    // TODO The owner can be removed
    // Anyone should be able to claim tokens
    address public owner;

    /*
     * Modifiers
     */

    modifier isOwner() {
        require(msg.sender == owner);
        _;
    }

    /*
     * Events
     */

    event Deployed();
    event Distributed(address[] indexed addresses);

    /*
      * Public functions
      */
    /// @dev Contract constructor function, sets the auction contract address.
    /// @param _auction_address Address of auction contract.
    function Distributor(address _auction_address) public {
        require(_auction_address != 0x0);

        owner = msg.sender;
        auction = DutchAuction(_auction_address);
        require(auction.owner_address() == owner);
        Deployed();
    }

    /// @notice Claim tokens in behalf of the following token owners: `addresses`.
    /// @dev Function that is called with an array of addresses for claiming tokens in their behalf.
    /// @param addresses Addresses of auction bidders that will be assigned tokens.
    function distribute(address[] addresses) public isOwner {
        for (uint8 i = 0; i < addresses.length; i++) {
            if (auction.bids(addresses[i]) > 0) {
                auction.claimTokens(addresses[i]);
            }
        }
        Distributed(addresses);
    }
}
