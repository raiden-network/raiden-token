pragma solidity ^0.4.11;

import './safe_math.sol';

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


/// @title Dutch auction contract - distribution of tokens using an auction.
/// @author [..] credits to Stefan George - <stefan.george@consensys.net>
contract DutchAuction {

    /*
     *  Events
     */
    event BidSubmission(address indexed sender, uint256 amount);

    /*
     *  Constants
     */
    uint constant public MAX_TOKENS_SOLD = 9000000 * 10**18; // 9M
    uint constant public WAITING_PERIOD = 7 days;

    /*
     *  Storage
     */
    Token public theToken;
    address public wallet;
    address public owner;
    uint public priceFactor;
    uint public startBlock;
    uint public endTime;
    uint public totalReceived;
    uint public totalDistributed;
    uint public finalPrice;
    mapping (address => uint) public bids;
    Stages public stage;

    /*
     *  Enums
     */
    enum Stages {
        AuctionDeployed,
        AuctionSetUp,
        AuctionStarted,
        AuctionEnded,
        TokensDistributed,
        TradingStarted,
        Done
    }

    /*
     *  Modifiers
     */
    modifier atStage(Stages _stage) {
        if (stage != _stage)
            // Contract not in expected stage
            throw;
        _;
    }

    modifier isOwner() {
        if (msg.sender != owner)
            // Only owner is allowed to proceed
            throw;
        _;
    }

    modifier isWallet() {
        if (msg.sender != wallet)
            // Only wallet is allowed to proceed
            throw;
        _;
    }

    modifier isValidPayload() {
        if (msg.data.length != 4 && msg.data.length != 36)
            throw;
        _;
    }

    modifier timedTransitions() {
        if (stage == Stages.AuctionStarted && calcTokenPrice() <= calcStopPrice()) {
            finalizeAuction();
        }
        if (stage == Stages.AuctionEnded && now > endTime + WAITING_PERIOD) {
            stage = Stages.TradingStarted;
        }
        _;
    }

    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets owner.
    /// @param _priceFactor Auction price factor.
    function DutchAuction(uint _priceFactor)
        public
    {
        if ( _priceFactor == 0)
            // Arguments are null.
            throw;
        owner = msg.sender;
        priceFactor = _priceFactor;
        stage = Stages.AuctionDeployed;
    }

    /// @dev Setup function sets external contracts' addresses.
    /// @param _theToken token address.
    function setup(address _theToken)
        public
        isOwner
        atStage(Stages.AuctionDeployed)
    {
        if (_theToken == 0)
            // Argument is null.
            throw;
        theToken = Token(_theToken);
        // Validate token balance
        if (theToken.balanceOf(this) != MAX_TOKENS_SOLD)
            throw;
        stage = Stages.AuctionSetUp;
    }

    /// @dev Changes auction start price factor before auction is started.
    /// @param _priceFactor Updated start price factor.
    function changeSettings(uint _priceFactor)
        public
        isWallet
        atStage(Stages.AuctionSetUp)
    {
        priceFactor = _priceFactor;
    }

    /// @dev Starts auction and sets startBlock.
    function startAuction()
        public
        isWallet
        atStage(Stages.AuctionSetUp)
    {
        stage = Stages.AuctionStarted;
        startBlock = block.number;
    }

    /// @dev Returns correct stage, even if a function with timedTransitions modifier has not yet been called yet.
    /// @return Returns current auction stage.
    function updateStage()
        public
        timedTransitions
        returns (Stages)
    {
        return stage;
    }

    /// --------------------------------- Auction Functions -------------------------------------------

    /// @dev Allows to send a bid to the auction.
    /// @param receiver Bid will be assigned to this address if set.
    function bid(address receiver)
        public
        payable
        isValidPayload
        timedTransitions
        atStage(Stages.AuctionStarted)
        returns (uint amount)
    {
        // If a bid is done on behalf of a user via ShapeShift, the receiver address is set.
        if (receiver == 0)
            receiver = msg.sender;
        amount = msg.value;
        uint maxWei = missingReserveToEndAuction();
        // Only invest maximum possible amount.
        if (amount > maxWei) {
            amount = maxWei;
            // Send change back to receiver address. In case of a ShapeShift bid the user receives the change back directly.
            if (!receiver.send(msg.value - amount))
                // Sending failed
                throw;
        }
        bids[receiver] += amount;
        totalReceived += amount;
        if (maxWei == amount)
            // When maxWei is equal to the big amount the auction is ended and finalizeAuction is triggered.
            finalizeAuction();
        BidSubmission(receiver, amount);
    }

    /// @dev Claims tokens for bidder after auction.
    /// @param receiver Tokens will be assigned to this address if set.
    function claimTokens(address receiver)
        public
        isValidPayload
        timedTransitions
        atStage(Stages.AuctionEnded) // FIXME
    {
        if (receiver == 0)
            receiver = msg.sender;
        uint num = bids[receiver] * 10**18 / finalPrice;
        totalDistributed += bids[receiver];
        bids[receiver] = 0;
        theToken.transfer(receiver, num);
        if (totalDistributed == totalReceived) {
            stage = Stages.TokensDistributed;
            transferReserve();
        }
    }


    /*
     *  Private functions
     */
    function finalizeAuction()
        private
    {
        stage = Stages.AuctionEnded;
        finalPrice = calcTokenPrice();
        assert(finalPrice == totalReceived / MAX_TOKENS_SOLD); // remove afer testing!!! use just one func to not get stuck!
        endTime = now;
    }

    /// @dev Transfers ETH reserve to token contract. Important to only do this after all tokens are distributed
    function transferReserve()
        private
        timedTransitions
        atStage(Stages.TokensDistributed)
    {
        if (!theToken.send(this.balance)) {
            throw;
        }
    }


    /// --------------------------------- Price Functions -------------------------------------------

    /// @dev Calculates current token price.
    /// @return Returns token price.
    function price()
        public
        constant
        returns (uint)
    {
        if (stage != Stages.AuctionStarted)
            return finalPrice;
        return calcTokenPrice();
    }


    /// @dev Calculates the token price at the current block heightm during the auction
    /// @return Returns the token price
    function calcTokenPrice()
        constant
        public
        atStage(Stages.AuctionStarted)
        returns (uint)
    {
        return priceFactor * 10**18 / (block.number - startBlock + 7500) + 1;
    }


    // @dev The marketcap at the current price
    // @return
    function mktcapAtPrice()
        constant
        public
        returns (uint)
    {
        return theToken.totalSupply() * price();
    }


    // @dev valuation is the difference between the marketcap and the reserve
    // @return
    function valuationAtPrice()
        constant
        public
        returns (uint)
    {
        return mktcapAtPrice() - reserveAtPrice(); // assuming no pre auction reserve
    }


    // @dev the required added reserve at the current price
    // @return
    function reserveAtPrice()
        constant
        public
        returns (uint)
    {
        return MAX_TOKENS_SOLD * price();
    }


    // @dev the reserve amount necessary to end the auction at the current price
    // @return
    function missingReserveToEndAuction()
        constant
        public
        returns (uint)
    {
        return SafeMath.max256(0, reserveAtPrice() - totalReceived);
    }

    // TODO
    /// @dev Calculates the auction price at which the auction should end
    /// @return Returns the auction stop price
    function calcStopPrice()
        constant
        public
        returns (uint)
    {
        return 1;
    }

}
