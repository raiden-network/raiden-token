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

    modifier auctionSettingsCanBeSetUp() {
        require(final_auction == false);
        require(stage == Stages.AuctionSetUp || stage == Stages.AuctionSettled);
        _;
    }

    event Deployed(address indexed _auction, uint _price_factor, uint _price_const);
    event Setup(uint indexed _stage, address indexed _mint);
    event SettingsChanged(uint indexed _stage, uint indexed _price_factor, uint indexed _price_const, bool _final_auction);
    event AuctionStarted(uint indexed _stage);

    event Ordered(address indexed _recipient, uint _sent_value, uint _accepted_value, uint indexed _missing_reserve);
    event ClaimedTokens(address indexed _recipient, uint _sent_value, uint _num);
    event AuctionEnded(uint indexed _stage, uint indexed _received_value, uint indexed  _total_issuance);
    event AuctionSettled(uint indexed _stage);
    event AuctionPrice(uint indexed _price, uint indexed _timestamp);
    event MissingReserve(uint indexed _balance, uint indexed _missing_reserve, uint indexed _timestamp);

    function Auction(uint _price_factor, uint _price_const) {
        price_factor = _price_factor;
        price_const = _price_const;
        stage = Stages.AuctionDeployed;
        owner = msg.sender;

        Deployed(this, _price_factor, _price_const);
    }

    // Fallback function
    function() payable {
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
        Setup(uint(stage), _mint);
    }

    function changeSettings(
        uint _price_factor,
        uint _price_const,
        bool _final_auction)

        public
        isOwner
        auctionSettingsCanBeSetUp
    {
        price_factor = _price_factor;
        price_const = _price_const;
        final_auction = _final_auction;
        stage = Stages.AuctionSetUp;

        SettingsChanged(uint(stage), price_factor, price_const, _final_auction);
    }

    function startAuction()
        public
        isOwner
        atStage(Stages.AuctionSetUp)
    {
        mint.auctionStarted();
        stage = Stages.AuctionStarted;
        startTimestamp = now;

        AuctionStarted(uint(stage));
    }

    // This is the function used by bidders
    function order()
        public
        payable
        isValidPayload
        atStage(Stages.AuctionStarted)
    {
        // Calculate missing balance until auction should end
        // !! at this point, auction balance contains the order value
        uint missing_reserve = missingReserveToEndAuction(mint.combinedReserve() - msg.value);
        uint accepted_value = SafeMath.min256(missing_reserve, msg.value);

        // Add value to bidder
        bidders[msg.sender] = SafeMath.add(bidders[msg.sender], accepted_value);

        // Send back funds if order is bigger than max auction reserve
        if (accepted_value < msg.value) {
            uint send_back = SafeMath.sub(msg.value, accepted_value);
            msg.sender.transfer(send_back);
        }

        Ordered(msg.sender, msg.value, accepted_value, missing_reserve);

        if (missing_reserve <= msg.value) {
            finalizeAuction();
        }
    }

    // Function used to assign auction tokens to each bidder
    // will be called from an external contract that loops through the accounts
    function claimTokens(address recipient)
        public
        isValidPayload
        atStage(Stages.AuctionEnded)
    {
        // Calculate number of tokens that will be issued for the amount paid, based on the final auction price
        uint num = bidders[recipient] * total_issuance / received_value;

        ClaimedTokens(recipient, bidders[recipient], num);

        // Keep track of claimed tokens
        issued_value += bidders[recipient];
        bidders[recipient] = 0;

        // Mint contract issues the tokens
        mint.issueFromAuction(recipient, num);

        // If all of the tokens from the previous auction have been issued,
        // we can start minting new tokens
        if (issued_value == received_value) {
            settleAuction();
        }
    }

    // Price function used in Dutch Auction; price starts high and decreases over time
    function price()
        public
        constant
        returns(uint)
    {
        uint elapsed = SafeMath.sub(now, startTimestamp);
        uint auction_price = SafeMath.add(price_factor / elapsed, price_const);
        AuctionPrice(auction_price, now);

        return auction_price;
    }

    // TODO
    function auctionIsActive()
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (bool)
    {
        if(price() > mint.curvePriceAtReserve(mint.combinedReserve()))
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
        return missingReserveToEndAuction(mint.combinedReserve());
    }

    // We have 2 functions here, because order() already updates the balance
    // We need to calculate missing reserve without the order value
    function missingReserveToEndAuction(uint current_reserve)
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (uint)
    {
        // Calculate reserve at the current auction price
        uint auction_price = price();
        auction_price -= mint.ownerFraction(auction_price);
        uint simulated_reserve = mint.curveReserveAtPrice(auction_price);

        // Auction ends when simulated auction reserve is < the current reserve (auction + mint reserve)
        if(simulated_reserve < current_reserve) {
            return 0;
        }

        uint missing_reserve = SafeMath.sub(simulated_reserve, current_reserve);
        MissingReserve(current_reserve, missing_reserve, now);

        return missing_reserve;
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

    function mintAsk()
        private
        returns (uint)
    {
        uint mint_price = mint.curvePriceAtReserve(mint.combinedReserve());
        mint_price -= mint.ownerFraction(mint_price);
        return mint_price;
    }

    // Auction has ended, we calculate total reserve and supply
    function finalizeAuction()
        private
        atStage(Stages.AuctionStarted)
    {
        // TODO
        // Utils.xassert(price(), mintAsk())

        // Get already issued tokens and the combined mint+auction reserve
        uint issued_supply = mint.issuedSupply();
        uint combined_reserve = mint.combinedReserve();

        // Number of tokens that should be issued at the current balance
        uint supply_at_reserve = mint.curveSupplyAtReserve(combined_reserve);

        // Calculate total number of tokens issued in this auction
        total_issuance = SafeMath.sub(supply_at_reserve, issued_supply);

        // Memorize received funds
        received_value = this.balance;

        // Send all funds to mint
        mint.fundsFromAuction.value(received_value)();

        stage = Stages.AuctionEnded;
        endTimestamp = now;
        AuctionEnded(uint(stage), received_value, total_issuance);

        // No need to claimTokens
        if(received_value == 0) {
            stage = Stages.AuctionSettled;
            AuctionSettled(uint(stage));
            mint.startMinting();
        }
    }

    function settleAuction()
        private
        atStage(Stages.AuctionEnded)
    {
        assert(issued_value == received_value);
        stage = Stages.AuctionSettled;
        AuctionSettled(uint(stage));
        mint.startMinting();
    }
}
