pragma solidity ^0.4.11;

import './safe_math.sol';
import './utils.sol';
import './mint.sol';

contract Auction {
    address public owner;
    Mint mint;

    // Price function parameters
    uint public price_factor;
    uint public price_const;

    // For calculating elapsed time for price
    uint public startTimestamp;
    uint public endTimestamp;

    // When auction ends, we memorize total value, tokens issued
    uint public received_value = 0;
    uint public total_issuance = 0;

    // Keep track of how many tokens were assigned to buyers
    uint public issued_value = 0;

    // No more auctions if this flag is true
    bool final_auction = false;

    mapping(address => uint256) public bidders;

    enum Stages {
        AuctionDeployed,
        AuctionSetUp,
        AuctionStarted,
        AuctionEnded,
        AuctionSettled
    }

    Stages public stage;

    modifier isOwner() {
        require(msg.sender == owner);
        _;
    }

    modifier isValidPayload() {
        require(msg.data.length == 4 || msg.data.length == 36);
        _;
    }

    modifier atStage(Stages _stage) {
        require(stage == _stage);
        _;
    }

    event LogAuctionEnded(uint price, uint issuance);
    event LogAuctionPrice(uint price);

    function Auction(uint _price_factor, uint _price_const) {
        price_factor = _price_factor;
        price_const = _price_const;
        stage = Stages.AuctionDeployed;
        owner = msg.sender;
    }

    // Fallback function
    function()
        payable
    {
        order();
    }

    function setup(address _mint)
        public
        isOwner
        atStage(Stages.AuctionDeployed)
    {
        require(_mint != 0x0);
        mint = Mint(_mint);
        stage = Stages.AuctionSetUp;
    }

    function changeSettings(
        uint _price_factor,
        uint _price_const,
        bool _final_auction)

        public
        isOwner
        atStage(Stages.AuctionSetUp)
    {
        price_factor = _price_factor;
        price_const = _price_const;
        final_auction = _final_auction;
    }

    function startAuction()
        public
        isOwner
        atStage(Stages.AuctionSetUp)
    {
        stage = Stages.AuctionStarted;
        startTimestamp = now;
    }

    // This is the function used by bidders
    function order()
        public
        payable
        isValidPayload
        atStage(Stages.AuctionStarted)
    {
        uint accepted_value = SafeMath.min256(missingReserveToEndAuction(), msg.value);
        if (accepted_value < msg.value) {
            msg.sender.transfer(SafeMath.sub(
                msg.value,
                accepted_value));
            finalizeAuction();
        }

        bidders[msg.sender] = SafeMath.add(bidders[msg.sender], accepted_value);
    }

    //
    function claimTokens(address recipient)
        public
        isValidPayload
        atStage(Stages.AuctionEnded)
    {
        // Calculate number of tokens that will be issued for the amount paid, based on the final auction price
        uint num = bidders[recipient] * total_issuance / received_value;

        // Keep track of claimed tokens
        issued_value += bidders[recipient];
        bidders[recipient] = 0;

        // Mint contract issues the tokens
        mint.issueFromAuction(recipient, num);

        // If all of the tokens from the previous auction have been issued,
        // we can start minting new tokens
        if (issued_value == received_value) {
            stage = Stages.AuctionSettled;
            mint.startMinting();
        }
    }

    // Price function used in Dutch Auction; price starts high and decreases over time
    function price()
        public
        constant
        returns(uint)
    {
        uint elapsed = SafeMath.sub(now, startTimestamp);
        return SafeMath.add(price_factor / elapsed, price_const);
    }

    // TODO remove? we do not need this anymore,
    // we apply missingReserveToEndAuction() in order() to see if auction has ended
    function auctionIsActive()
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (bool)
    {
        if(price() > mint.curvePriceAtReserve(mint.totalReserve()))
            return true;
        return false;
    }

    // Calculate how much currency we need to attain
    // a reserve / balance that would end the auction
    function missingReserveToEndAuction()
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (uint)
    {
        // Calculate reserve at the current auction price
        uint auction_price = price();
        auction_price -= mint.ownerFraction(auction_price);
        uint simulated_reserve = mint.curveReserveAtPrice(auction_price);
        uint current_reserve = mint.totalReserve();

        // Auction ends when simulated auction reserve is < the current reserve (auction + mint reserve)
        if(simulated_reserve < current_reserve) {
            return 0;
        }
        return SafeMath.sub(simulated_reserve, current_reserve);
    }

    // The market cap if the auction would end at the current price
    function auctionMarketCap()
        public
        constant
        returns (uint)
    {
        uint auction_price = price();

        // We calculate the supply based on the current auction price
        uint auction_supply = mint.curveSupplyAtPrice(auction_price);

        return SafeMath.mul(auction_price, auction_supply);
    }

    // The valuation if the auction would end at the current price
    function auctionValuation()
        public
        constant
        returns (uint)
    {
        return mint.ownerFraction(auctionMarketCap());
    }

    // Auction has ended, we calculate total reserve and supply
    function finalizeAuction()
        private
        atStage(Stages.AuctionStarted)
    {
        uint mint_price = mint.curvePriceAtReserve(mint.totalReserve());
        mint_price -= mint.ownerFraction(mint_price);
        require(price() <= mint_price);

        // Memorize received funds
        received_value = this.balance;

        // Calculate total number of tokens based on the received reserve
        total_issuance = SafeMath.sub(
            mint.curveSupplyAtReserve(mint.totalReserve()),
            mint.totalSupply()
        );

        // Send all funds to mint
        mint.fundsFromAuction.value(this.balance);

        stage = Stages.AuctionEnded;
        endTimestamp = now;
        LogAuctionEnded(received_value, total_issuance);
    }
}
