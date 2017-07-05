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
        uint _base_price, // 24 decimals
        uint _price_factor, // 24 decimals
        uint _owner_fr,
        uint _owner_fr_dec)
    {
        owner = msg.sender;
        base_price = _base_price;
        price_factor = _price_factor;
        owner_fr = _owner_fr;
        owner_fr_dec = _owner_fr_dec;

        // Example (10, 2) means 10%, we cannot have 1000%
        assert(Utils.num_digits(owner_fr) <= owner_fr_dec);

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

    function changeSettings(
        uint _base_price,
        uint _price_factor,
        uint _owner_fr,
        uint _owner_fr_dec)

        public
        isOwner
        atStage(Stages.MintSetUp)
    {
        base_price = _base_price;
        price_factor = _price_factor;
        owner_fr = _owner_fr;
        owner_fr_dec = _owner_fr_dec;
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
        return SafeMath.add(
            base_price,
            SafeMath.mul(_supply, price_factor)
        );
    }

    function supply(uint _reserve)
        constant
        returns (uint)
    {
        uint sqrt = Utils.sqrt(
            SafeMath.add(
                base_price**2,
                SafeMath.mul(
                    SafeMath.mul(2, _reserve),
                    price_factor)
        ));
        return SafeMath.sub(sqrt, base_price) / price_factor;
    }

    function reserve(uint _supply)
        constant
        returns (uint)
    {
        return SafeMath.add(
            SafeMath.mul(base_price, _supply),
            SafeMath.mul(
                SafeMath.div(price_factor, 2),
                _supply**2)
        );
    }

    function supplyAtPrice(uint _price)
        constant
        returns (uint)
    {
        assert(_price >= base_price);
        return SafeMath.sub(_price, base_price) / price_factor;
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

    // We apply this on the currency value to lose less when rounding
    function ownerFraction(uint _value)
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(_value, owner_fr) / 10**owner_fr_dec;
    }
}
