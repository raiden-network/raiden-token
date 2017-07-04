pragma solidity ^0.4.11;

import './auction.sol';
import './ctoken.sol';
import './safe_math.sol';

contract Mint {
    address public owner;
    Auction auction;
    ContinuousToken token;
    uint base_price;
    uint price_factor;
    uint price_factor_dec;
    uint owner_fr;
    uint owner_fr_dec;

    enum Stages {
        MintDeployed,
        MintSetUp,
        AuctionEnded, // after Auction called
        TradingStarted
    }

    Stages public stage;

    modifier isOwner() {
        require(msg.sender == owner);
        _;
    }

    modifier isAuction() {
        require(msg.sender == address(auction));
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

    function Mint(
        uint _base_price,
        uint _price_factor,
        uint _price_factor_dec,
        uint _owner_fr,
        uint _owner_fr_dec)
    {
        owner = msg.sender;
        base_price = _base_price;
        price_factor = _price_factor;
        price_factor_dec = _price_factor_dec;
        owner_fr = _owner_fr;
        owner_fr_dec = _owner_fr_dec;

        stage = Stages.MintDeployed;
    }

    // Fallback function
    function() {
        buy();
    }

    function setup(address _auction, address _token)
        public
        isOwner
        atStage(Stages.MintDeployed)
    {
        auction = Auction(_auction);
        token = ContinuousToken(_token);
        stage = Stages.MintSetUp;
    }

    function buyPreAuction(address recipient)
        public
        payable
        isOwner
        isValidPayload
        atStage(Stages.MintSetUp)
    {
        // Calculate no of tokens based on curve price
        uint num = SafeMath.div(msg.value, price(totalSupply()));
        token.issue(recipient, num);
    }

    function buy()
        public
        payable
        isValidPayload
        atStage(Stages.TradingStarted)
    {

        // TODO verify; calc the num of newly issued tokens based on the eth amount sent
        uint num = supply(msg.value);

        token.issue(msg.sender, num);
    }

    function sell(uint num)
        atStage(Stages.TradingStarted)
    {
        token.destroy(msg.sender, num);
        msg.sender.transfer(purchaseCost(num));
    }

    function totalSupply()
        public
        constant
        returns (uint)
    {
        return token.totalSupply();
    }

    function startTrading()
        isAuction
        atStage(Stages.AuctionEnded)
    {
        stage = Stages.TradingStarted;
    }

    function fundsFromAuction()
        public
        payable
        isAuction
        atStage(Stages.MintSetUp)
    {
        stage = Stages.AuctionEnded;
    }

    function issueFromAuction(address recipient, uint num)
        isAuction
        atStage(Stages.AuctionEnded)
    {
        token.issue(recipient, num);
    }

    function price(uint _supply)
        constant
        returns (uint)
    {
        // TODO factor?
        return SafeMath.add(base_price, priceFactor(_supply));
    }

    function supply(uint _reserve)
        constant
        returns (uint)
    {
        if(_reserve == 0x0) {
            _reserve = this.balance;
        }
        // TODO factor?
        uint sqrt = Utils.sqrt(
            SafeMath.add(
                base_price**2,
                priceFactor(SafeMath.mul(2, _reserve))
            ));
        return SafeMath.sub(sqrt, base_price) / priceFactor(1);
    }

    function reserve(uint _supply)
        constant
        returns (uint)
    {
        if(_supply == 0x0) {
            _supply = totalSupply();
        }

        // TODO factor?
        return SafeMath.add(
            SafeMath.mul(base_price, _supply),
            priceFactor(_supply**2) / 2
        );
    }

    function supplyAtPrice(uint _price)
        constant
        returns (uint)
    {
        // TODO factor?
        return SafeMath.sub(_price, base_price) / priceFactor(1);
    }

    function reserveAtPrice(uint _price)
        constant
        returns (uint)
    {
        assert(_price >= 0);
        return reserve(supplyAtPrice(_price));
    }

    // Calculate cost for a number of tokens
    function cost(uint _supply, uint _num)
        constant
        returns (uint)
    {
        return SafeMath.sub(
            reserve(SafeMath.add(_supply, _num)),
            reserve(_supply)
        );
    }

    // TODO
    // function curve_newly_issuable(supply, added_reserve) constant {};

    // TODO why 2 marketCaps?
    function curveMarketCap(uint _supply)
        constant
        returns (uint)
    {
        return SafeMath.mul(
            price(totalSupply()),
            totalSupply()
        );
    }

    function marketCap()
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(ask(), token.totalSupply());
    }

    // TODO function curve_supply_at_mktcap(m) constant {}
    /*function supplyAtMarketCap(self, m, skipped=0) returns (uint) {
        b, f = self.b, self.f
        f = self.f
        b = (self.b + skipped * self.f)
        s = (-b + sqrt(b**2 - 4 * f * -m)) / (2 * f)
        return s
    }*/

    function saleCost(uint num)
        public
        constant
        returns (uint)
    {
        // TODO check this
        uint maxSupply = SafeMath.max256(
            supply(supplyAtPrice(auction.price())), supply(this.balance)
        );

        // TODO check beneficiary fraction
        // apply beneficiary fraction to wei - bigger number, we lose less when rounding

        return cost(
            SafeMath.sub(
                maxSupply,
                ownerFraction(maxSupply)
            ),
            num
        );
    }

    // TODO function purchase_cost(num, supply) constant {}; //
    function purchaseCost(uint _num)
        constant
        returns (uint)
    {
        // the value offered if tokens are bought back

        if(totalSupply() == 0) {
            return 0;
        }

        assert(_num >= 0 && _num <= totalSupply());
        uint c = SafeMath.mul(this.balance, _num) / totalSupply();
        return c;
    }

    function ask()
        public
        constant
        returns (uint)
    {
        return saleCost(1);
    }

    // TODO: function valuation() constant {}; //  # (ask - bid) * supply
    function valuation()
        public
        constant
        returns (uint)
    {
        return SafeMath.max256(0, SafeMath.sub(marketCap(), this.balance));
    }

    // We apply this for the supply, in order to lose less when rounding (wei)
    function ownerFraction(uint _supply)
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(_supply, owner_fr) / 10**owner_fr_dec;
    }

    // We apply this for the supply, in order to lose less when rounding (wei)
    function priceFactor(uint _supply)
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(_supply, price_factor) / 10**price_factor_dec;
    }
}
