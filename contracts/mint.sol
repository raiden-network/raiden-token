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
        AuctionEnded,
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
    function()
        payable
    {
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
        uint num = SafeMath.sub(
            curveSupplyAtReserve(SafeMath.add(this.balance, msg.value)),
            curveSupplyAtReserve(this.balance)
        );
        issue(recipient, num);
    }

    function buy()
        public
        payable
        isValidPayload
        atStage(Stages.TradingStarted)
    {

        // calculate the num of newly issued tokens based on the added reserve (sent currency)
        uint num = curveIssuable(supplyAtReserve(), msg.value);
        issue(msg.sender, num);
    }

    function sell(uint num)
        public
        atStage(Stages.TradingStarted)
    {
        token.destroy(msg.sender, num);
        msg.sender.transfer(purchaseCost(num));
    }

    function burn(uint num)
        public
        atStage(Stages.TradingStarted)
    {
        token.destroy(msg.sender, num);
    }

    function totalSupply()
        public
        constant
        returns (uint)
    {
        return token.totalSupply();
    }

    function startTrading()
        public
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
        public
        isAuction
        atStage(Stages.AuctionEnded)
    {
        issue(recipient, num);
    }

    function curvePriceAtSupply(uint _supply)
        public
        constant
        returns (uint)
    {
         uint price_value = SafeMath.add(
            base_price,
            SafeMath.mul(_supply, price_factor)
        );
        return price_value;
    }

    function curvePriceAtReserve(uint _reserve)
        public
        constant
        returns (uint)
    {
        return curvePriceAtSupply(curveSupplyAtReserve(_reserve));
    }

    function curveSupplyAtReserve(uint _reserve)
        public
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
        uint supply_value = SafeMath.sub(sqrt, base_price) / price_factor;
        return supply_value;
    }

    function curveReserveAtSupply(uint _supply)
        public
        constant
        returns (uint)
    {
        uint reserve_value = SafeMath.add(
            SafeMath.mul(base_price, _supply),
            SafeMath.mul(
                SafeMath.div(price_factor, 2),
                _supply**2)
        );
        return reserve_value;
    }

    function curveSupplyAtPrice(uint _price)
        public
        constant
        returns (uint)
    {
        assert(_price >= base_price);
        return SafeMath.sub(_price, base_price) / price_factor;
    }

    function curveReserveAtPrice(uint _price)
        public
        constant
        returns (uint)
    {
        assert(_price >= 0);
        return curveReserveAtSupply(curveSupplyAtPrice(_price));
    }

    // Calculate cost for a number of tokens
    // curveAddedReserveAtAddedSupply ?
    function curveCost(uint _supply, uint _num)
        public
        constant
        returns (uint)
    {
        uint cost_value = SafeMath.sub(
            curveReserveAtSupply(SafeMath.add(_supply, _num)),
            curveReserveAtSupply(_supply)
        );
        return cost_value;
    }

    // Calculate number of tokens issued for a certain value at a certain supply
    // curveAddedSupplyAtAddedReserve ?
    function curveIssuable(uint _supply, uint added_reserve)
        public
        constant
        returns (uint)
    {
        uint reserve_value = curveReserveAtSupply(_supply);
        uint issued_tokens = SafeMath.sub(
            curveSupplyAtReserve(SafeMath.add(reserve_value, added_reserve)),
            _supply
        );
        return issued_tokens;
    }

    function curveMarketCapAtSupply(uint _supply)
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(curvePriceAtSupply(_supply), _supply);
    }

    // TODO function curve_supply_at_mktcap(m) constant {}
    /*function curveSupplyAtMarketCap(m, skipped=0) returns (uint) {
        b, f = self.b, self.f
        f = self.f
        b = (self.b + skipped * self.f)
        s = (-b + sqrt(b**2 - 4 * f * -m)) / (2 * f)
        return s
    }*/

    function supplyAtReserve()
        public
        constant
        returns (uint)
    {
        return curveSupplyAtReserve(this.balance);
    }

    function marketCap()
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(ask(), token.totalSupply());
    }

    function ask()
        public
        constant
        returns (uint)
    {
        return saleCost(1);
    }

    function saleCost(uint num)
        public
        constant
        returns (uint)
    {
        uint sale_cost = curveCost(
            supplyAtReserve(),
            SafeMath.sub(num, ownerFraction(num))
        );
        return sale_cost;
    }

    function purchaseCost(uint _num)
        public
        constant
        returns (uint)
    {
        // the value offered if tokens are bought back

        if(totalSupply() == 0) {
            return 0;
        }

        assert(_num <= totalSupply());
        uint purchase_cost = SafeMath.mul(this.balance, _num) / totalSupply();
        return purchase_cost;
    }

    // TODO: function valuation() constant {}; //  # (ask - bid) * supply
    function valuation()
        public
        constant
        returns (uint)
    {
        uint val = SafeMath.max256(0, SafeMath.sub(marketCap(), this.balance));
        return val;
    }

    // We apply this on the currency value to lose less when rounding
    function ownerFraction(uint _value)
        public
        constant
        returns (uint)
    {
        return SafeMath.mul(_value, owner_fr) / 10**owner_fr_dec;
    }

    // Issuing tokens pre-auction or post-auction
    function issue(address recipient, uint num)
        private
        returns (uint)
    {
        require(stage == Stages.MintSetUp || stage == Stages.TradingStarted);
        uint owner_num = ownerFraction(num);
        uint recipient_num = SafeMath.sub(num, owner_num);

        token.issue(recipient, recipient_num);
        token.issue(owner, owner_num);

        return recipient_num;
    }
}
