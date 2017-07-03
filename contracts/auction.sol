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

    modifier isValidPayload() {
        require(msg.data.length == 4 || msg.data.length == 36);
        _;
    }

    modifier atStage(Stages _stage) {
        require(stage == _stage);
        _;
    }

    event logAuctionEnded(uint price, uint issuance);

    function Auction(uint _factor, uint _const) {
        factor = _factor;
        const = _const;
        stage = Stages.AuctionDeployed;
        owner = msg.sender;
    }

    function setup(address _token) public isOwner atStage(Stages.AuctionDeployed) {

        // register token
        require(_token != 0x0);
        // TODO: what's the benefit of doing this:
        token = ContinuousToken(_token);

        stage = Stages.AuctionSetUp;

        require(address(token) == _token);
        require(stage == Stages.AuctionSetUp);
    }

    function startAuction() public isOwner atStage(Stages.AuctionSetUp) {
        stage = Stages.AuctionStarted;
        startBlock = block.number;
    }

    // TODO: check if call from token!
    function finalizeAuction() {
        assert(_notional_supply() >= _simulated_supply());
        assert(isauction());

        uint price = ask();
        uint total_issuance = _notional_supply();
        logAuctionEnded(price, total_issuance);

        for(uint i = 0; i < addresses.length; i++) {
            uint num_issued = total_issuance * bidders[addresses[i]] / token.reserve_value();
            token._issue(num_issued, addresses[i]);
        }

        Utils.xassert(token.reserve(token.totalSupply()), token.reserve_value(), 0, 0);
        Utils.xassert(token.totalSupply(), _notional_supply(), 0, 0);

        // assert it is not used anymore, even if tokens would be destroyed
        assert(token.totalSupply() == total_issuance);
        assert(token.totalSupply() > 0);

        stage = Stages.AuctionEnded;
        endBlock = now;
    }

    function isauction() public returns (bool) {
        return stage != Stages.AuctionEnded && _simulated_supply() >= _notional_supply();
    }

    function finalized() public returns (bool) {
        return stage == Stages.AuctionEnded;
    }

    // TODO order called only from ContinuousToken
    function order(address _recipient, uint _value) public {
        // TODO: right way of testing this
        if(bidders[_recipient] == 0) {
            bidders[_recipient] = 0;
            addresses.push(_recipient);
        }
        bidders[_recipient] += _value;
    }

    function price_surcharge() returns(uint) {
        uint elapsed = block.number - startBlock;
        return factor / elapsed + const;
    }

    function ask() returns (uint) {
        return _sale_cost(1);
    }

    function missing_reserve_to_end_auction() returns (uint) {
        return SafeMath.max256(0, token.reserve(_simulated_supply()) - token.reserve_value());
    }

    function _notional_supply() returns (uint) {
        /*
        supply according to reserve_value
        */
        return token.supply(token.reserve_value());
    }

    function _simulated_supply() returns (uint) {
        /*
        current auction price converted to additional supply
        note: this is virtual skipped supply,
        so we must not include the skipped supply
        */
        if(isauction() && price_surcharge() >= token.base_price())
            return token.supply_at_price(price_surcharge());
        return 0;
    }

    function _arithmetic_supply() returns (uint) {
        if(isauction())
            return _simulated_supply();
        return _notional_supply();
    }

    // cost of selling, purchasing tokens
    function _sale_cost(uint _num) returns (uint) {
        assert(_num >= 0);
        // TODO: replace beneficiary
        // uint added = _num / (1 - beneficiary.get_fraction());
        // return token.cost(_arithmetic_supply(), added);

        // apply beneficiary fraction to wei - bigger number, we lose less when rounding
        uint arithm = _arithmetic_supply();
        return  token.cost(arithm - token.benfr(arithm) , _num);
    }

    function mktcap() returns (uint) {
        return ask() * token.totalSupply();
    }

    function valuation() returns (uint) {
        return SafeMath.max256(0, mktcap() - token.reserve_value());
    }

    function max_mktcap() returns (uint) {
        uint vsupply = token.supply_at_price(ask());
        return ask() * vsupply;
    }

    function max_valuation() returns (uint) {
        // FIXME
        // TODO replace beneficiary
        // return max_mktcap() * beneficiary.get_fraction();

        return token.benfr(max_mktcap());
    }

    /*
    function curve_price_auction() returns (uint) {
        return token.cost(_arithmetic_supply(), 1);
    }

    function curve_price() returns (uint) {
        return token.cost(_notional_supply(), 1);
    }
    */
}
