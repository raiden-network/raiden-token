pragma solidity ^0.4.11;

import './safe_math.sol';
import './token.sol';

/// @title Dutch auction contract - distribution of tokens using an auction.
/// @author [..] credits to Stefan George - <stefan.george@consensys.net>
contract DutchAuction {

    /*
     *  Constants
     */
    uint constant multiplier = 10**18;
    uint constant public MAX_TOKENS_SOLD = 9000000 * multiplier; // 9M
    uint constant public WAITING_PERIOD = 7 days;

    /*
     *  Storage
     */
    ReserveToken public token;
    address public wallet;
    address public owner;
    uint public price_factor;
    uint public start_block;
    uint public end_time;
    uint public funds_claimed;
    uint public final_price;
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
        TradingStarted
    }

    /*
     *  Modifiers
     */
    modifier atStage(Stages _stage) {
        require(stage == _stage);
        _;
    }

    modifier isOwner() {
        require(msg.sender == owner);
        _;
    }

    modifier isValidPayload() {
        require(msg.data.length == 4 || msg.data.length == 36);
        _;
    }

    modifier timedTransitions() {
        if (stage == Stages.AuctionStarted && calcTokenPrice() <= calcStopPrice()) {
            finalizeAuction();
        }
        if (stage == Stages.AuctionEnded && now > end_time + WAITING_PERIOD) {
            stage = Stages.TradingStarted;
        }
        _;
    }

    /*
     *  Events
     */

    event Deployed(address indexed auction, uint price_factor);
    event Setup();
    event SettingsChanged(uint indexed price_factor);
    event AuctionStarted(uint indexed block_number);
    event BidSubmission(address indexed sender, uint amount, uint returned_amount, uint indexed missing_reserve);
    event ClaimedTokens(address indexed recipient, uint sent_amount, uint num);
    event AuctionEnded(uint indexed final_price);
    event TokensDistributed();
    event TradingStarted();

    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets owner.
    /// @param _price_factor Auction price factor.
    function DutchAuction(uint _price_factor)
        public
    {
        if ( _price_factor == 0) {
            // Arguments are null.
            throw;
        }
        owner = msg.sender;
        price_factor = _price_factor;
        stage = Stages.AuctionDeployed;
        Deployed(this, _price_factor);
    }

    /// @dev Setup function sets external contracts' addresses.
    /// @param _token token address.
    function setup(address _token)
        public
        isOwner
        atStage(Stages.AuctionDeployed)
    {
        require(_token != 0x0);
        token = ReserveToken(_token);

        // Validate token balance
        assert(token.balanceOf(this) == MAX_TOKENS_SOLD);

        stage = Stages.AuctionSetUp;
        Setup();
    }

    /// @dev Changes auction start price factor before auction is started.
    /// @param _price_factor Updated start price factor.
    function changeSettings(uint _price_factor)
        public
        atStage(Stages.AuctionSetUp)
    {
        price_factor = _price_factor;
        SettingsChanged(price_factor);
    }

    /// @dev Starts auction and sets start_block.
    function startAuction()
        public
        isOwner
        atStage(Stages.AuctionSetUp)
    {
        stage = Stages.AuctionStarted;
        start_block = block.number;
        AuctionStarted(start_block);
    }

    /// --------------------------------- Auction Functions -------------------------------------------

    /// @dev Allows to send a bid to the auction.
    function bid()
        public
        payable
        isValidPayload
        //timedTransitions
        atStage(Stages.AuctionStarted)
    {
        // calcTokenPrice() <= calcStopPrice() -> finalizeAuction (timedTransitions)
        uint amount = msg.value;
        uint maxWei = missingReserveToEndAuction(this.balance - amount);

        // Only invest maximum possible amount.
        if (amount > maxWei) {
            amount = maxWei;
            // Send change back to receiver address.
            msg.sender.transfer(msg.value - amount);
        }
        bids[msg.sender] += amount;
        BidSubmission(msg.sender, amount, msg.value - amount, maxWei);

        if (maxWei == amount) {
            // When maxWei is equal to the big amount the auction is ended and finalizeAuction is triggered.
            finalizeAuction();
        }
    }

    /// @dev Claims tokens for bidder after auction. To be used if tokens can be claimed by bidders, individually.
    function claimTokens()
        public
        //timedTransitions
        atStage(Stages.AuctionEnded)
    {
        claimTokens(msg.sender);
    }

    /// @dev Claims tokens for bidder after auction.
    /// @param receiver Tokens will be assigned to this address if set.
    function claimTokens(address receiver)
        public
        isValidPayload
        atStage(Stages.AuctionEnded)
    {
        require(receiver != 0x0);
        uint num = bids[receiver] * multiplier / final_price;
        funds_claimed += bids[receiver];

        ClaimedTokens(receiver, bids[receiver], num);

        bids[receiver] = 0;
        assert(token.transfer(receiver, num));

        if (funds_claimed == this.balance) {
            stage = Stages.TokensDistributed;
            TokensDistributed();
            transferReserveToToken();
        }
    }

    /*
     *  Private functions
     */
    function finalizeAuction()
        private
        atStage(Stages.AuctionStarted)
    {
        // TODO block number as argument
        final_price = calcTokenPrice();
        assert(final_price == this.balance / MAX_TOKENS_SOLD); // remove afer testing!!! use just one func to not get stuck!
        end_time = now;
        stage = Stages.AuctionEnded;
        AuctionEnded(final_price);
    }

    function transferReserveToToken()
        private
        atStage(Stages.TokensDistributed)
    {
        token.receiveReserve.value(this.balance)();
        stage = Stages.TradingStarted;
        TradingStarted();
    }

    /// --------------------------------- Price Functions -------------------------------------------

    /// @dev Calculates current token price.
    /// @return Returns token price.
    function price()
        public
        constant
        returns (uint)
    {
        if (stage != Stages.AuctionStarted) {
            return final_price;
        }
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
        return price_factor * multiplier / (block.number - start_block + 7500) + 1;
    }


    // @dev The marketcap at the current price
    // @return
    function mktcapAtPrice()
        constant
        public
        returns (uint)
    {
        return token.totalSupply() * price();
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
        return missingReserveToEndAuction(this.balance);
    }

    // @dev the reserve amount necessary to end the auction at the current price
    // @dev 2 function definitions because order() already updates the reserve
    // @return
    function missingReserveToEndAuction(uint reserve)
        constant
        public
        returns (uint)
    {
        return SafeMath.max256(0, reserveAtPrice() - reserve);
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
