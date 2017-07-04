pragma solidity ^0.4.11;

import './safe_math.sol';
import './utils.sol';
import './ctoken.sol';

contract Auction {
    address public owner;
    uint factor;
    uint const;
    uint public startBlock;
    uint public endBlock;
    mapping(address => uint256) public bidders; // value_by_buyer
    // For iterating over the addresses
    address[] addresses;
    ContinuousToken token;

    enum Stages {
        AuctionDeployed,
        AuctionSetUp,
        AuctionStarted,
        AuctionEnded,
        TradingStarted
    }

    Stages public stage;

    modifier isOwner() {
        require(msg.sender == owner);
        _;
    }

    modifier isToken() {
        require(msg.sender == address(token));
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

    function Auction(uint _factor, uint _const) {
        factor = _factor;
        const = _const;
        stage = Stages.AuctionDeployed;
        owner = msg.sender;
    }

    function setup(address _token)
        public
        isOwner
        atStage(Stages.AuctionDeployed)
    {

        // Register token
        require(_token != 0x0);
        token = ContinuousToken(_token);

        stage = Stages.AuctionSetUp;

        require(address(token) == _token);
        require(stage == Stages.AuctionSetUp);
    }

    function startAuction()
        public
        isOwner
        atStage(Stages.AuctionSetUp)
    {
        stage = Stages.AuctionStarted;
        startBlock = block.number;
    }

    // TODO check if call from token; public?
    function finalizeAuction()
        atStage(Stages.AuctionStarted)
    {
        require(reserveSupply() >= simulatedSupply());

        uint price = ask();
        uint total_issuance = reserveSupply();
        LogAuctionEnded(price, total_issuance);

        for(uint i = 0; i < addresses.length; i++) {
            uint num_issued = SafeMath.mul(total_issuance, bidders[addresses[i]]) / token.reserve_value();
            token._issue(num_issued, addresses[i]);
        }

        Utils.xassert(token.reserve(token.totalSupply()), token.reserve_value(), 0, 0);
        Utils.xassert(token.totalSupply(), reserveSupply(), 0, 0);

        assert(token.totalSupply() == total_issuance);
        assert(token.totalSupply() > 0);

        stage = Stages.AuctionEnded;
        endBlock = now;
    }

    function isAuction()
        public
        constant
        returns (bool)
    {
        return simulatedSupply() >= reserveSupply();
    }

    function finalized()
        public
        constant
        returns (bool)
    {
        return stage == Stages.AuctionEnded;
    }

    function order(address _recipient, uint _value)
        public
        isToken
    {
        // TODO optimal way?
        if(bidders[_recipient] == 0) {
            bidders[_recipient] = 0;
            addresses.push(_recipient);
        }
        bidders[_recipient] = SafeMath.add(bidders[_recipient], _value);
    }

    function ask()
        public
        constant
        returns (uint)
    {
        return saleCost(1);
    }

    function missingReserveToEndAuction()
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (uint)
    {
        uint missing_reserve = SafeMath.sub(
            token.reserve(simulatedSupply()),
            token.reserve_value()
        );
        return SafeMath.max256(0, missing_reserve);
    }

    function reserveSupply()
        public
        constant
        returns (uint)
    {
        // supply according to reserve_value
        return token.supply(token.reserve_value());
    }

    function simulatedSupply()
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (uint)
    {
        // get supply based on the simulated price at current timestamp
        if(isAuction() && priceSurcharge() >= token.base_price()) {
            return token.supplyAtPrice(priceSurcharge());
        }
        return 0;
    }

    function maxSupply()
        public
        constant
        returns (uint)
    {
        return SafeMax.max256(simulatedSupply(), reserveSupply());
    }

    function marketCap()
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(ask(), token.totalSupply());
    }

    function valuation()
        public
        constant
        returns (uint)
    {
        return SafeMath.max256(0, SafeMath.sub(marketCap(), token.reserve_value()));
    }

    function maxMarketCap()
        public
        constant
        returns (uint)
    {
        uint vsupply = token.supplyAtPrice(ask());
        return SafeMath.mul(ask(), vsupply);
    }

    // TODO do we need this?
    function maxValuation()
        public
        constant
        returns (uint)
    {
        // FIXME
        // TODO check beneficiary fraction
        // return maxMarketCap() * beneficiary.get_fraction();

        return token.beneficiaryFraction(maxMarketCap());
    }

    // Cost of selling, purchasing tokens
    function saleCost(uint _num)
        public
        constant
        returns (uint)
    {
        // TODO check beneficiary fraction
        // uint added = _num / (1 - beneficiary.get_fraction());
        // return token.cost(maxSupply(), added);

        // apply beneficiary fraction to wei - bigger number, we lose less when rounding
        uint arithm = maxSupply();
        return token.cost(
            SafeMath.sub(
                arithm,
                token.beneficiaryFraction(arithm)
            ), _num);
    }

    function priceSurcharge()
        private
        constant
        returns(uint)
    {
        uint elapsed = SafeMath.sub(block.number, startBlock);
        return SafeMath.add(factor / elapsed, const);
    }

    // TODO do we need this?
    function curvePriceAuction()
        constant
        returns (uint)
    {
        return token.cost(maxSupply(), 1);
    }

    function curvePrice()
        constant
        returns (uint)
    {
        return token.cost(reserveSupply(), 1);
    }
}
