pragma solidity ^0.4.11;

import "./safe_math.sol";
import "./utils.sol";
import "./ctoken.sol";

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

    // TODO check if call from token
    function finalizeAuction()
        atStage(Stages.AuctionStarted)
    {
        require(notional_supply() >= simulated_supply());

        uint price = ask();
        uint total_issuance = notional_supply();
        LogAuctionEnded(price, total_issuance);

        for(uint i = 0; i < addresses.length; i++) {
            uint num_issued = SafeMath.mul(total_issuance, bidders[addresses[i]]) / token.reserve_value();
            token._issue(num_issued, addresses[i]);
        }

        Utils.xassert(token.reserve(token.totalSupply()), token.reserve_value(), 0, 0);
        Utils.xassert(token.totalSupply(), notional_supply(), 0, 0);

        // assert it is not used anymore, even if tokens would be destroyed
        assert(token.totalSupply() == total_issuance);
        assert(token.totalSupply() > 0);

        stage = Stages.AuctionEnded;
        endBlock = now;
    }

    function isauction()
        public
        constant
        returns (bool)
    {
        return simulated_supply() >= notional_supply();
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

    function price_surcharge()
        constant
        returns(uint)
    {
        uint elapsed = SafeMath.sub(block.number, startBlock);
        return SafeMath.add(factor / elapsed, const);
    }

    function ask()
        public
        constant
        returns (uint)
    {
        return _sale_cost(1);
    }

    function missing_reserve_to_end_auction()
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (uint)
    {
        uint missing_reserve = SafeMath.sub(
            token.reserve(simulated_supply()),
            token.reserve_value()
        );
        return SafeMath.max256(0, missing_reserve);
    }

    function notional_supply()
        public
        constant
        returns (uint)
    {
        /*
        supply according to reserve_value
        */
        return token.supply(token.reserve_value());
    }

    function simulated_supply()
        public
        constant
        atStage(Stages.AuctionStarted)
        returns (uint)
    {
        /*
        current auction price converted to additional supply
        note: this is virtual skipped supply,
        so we must not include the skipped supply
        */
        if(isauction() && price_surcharge() >= token.base_price())
            return token.supply_at_price(price_surcharge());
        return 0;
    }

    function _arithmetic_supply()
        public
        constant
        returns (uint)
    {
        if(isauction())
            return simulated_supply();
        return notional_supply();
    }

    // Cost of selling, purchasing tokens
    function _sale_cost(uint _num)
        constant
        returns (uint)
    {
        // TODO check beneficiary fraction
        // uint added = _num / (1 - beneficiary.get_fraction());
        // return token.cost(_arithmetic_supply(), added);

        // apply beneficiary fraction to wei - bigger number, we lose less when rounding
        uint arithm = _arithmetic_supply();
        return token.cost(
            SafeMath.sub(
                arithm,
                token.benfr(arithm)
            ), _num);
    }

    function mktcap()
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
        return SafeMath.max256(0, SafeMath.sub(mktcap(), token.reserve_value()));
    }

    function max_mktcap()
        public
        constant
        returns (uint)
    {
        uint vsupply = token.supply_at_price(ask());
        return SafeMath.mul(ask(), vsupply);
    }

    function max_valuation()
        public
        constant
        returns (uint)
    {
        // FIXME
        // TODO check beneficiary fraction
        // return max_mktcap() * beneficiary.get_fraction();

        return token.benfr(max_mktcap());
    }

    function curve_price_auction()
        constant
        returns (uint)
    {
        return token.cost(_arithmetic_supply(), 1);
    }

    function curve_price()
        constant
        returns (uint)
    {
        return token.cost(notional_supply(), 1);
    }
}
