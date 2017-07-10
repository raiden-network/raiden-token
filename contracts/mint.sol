pragma solidity ^0.4.11;

import './auction.sol';
import './ctoken.sol';
import './safe_math.sol';
import './utils.sol';

contract Mint {
    address public owner;
    Auction auction;
    ContinuousToken token;

    // Base price and factor used in the price-supply curve functions
    uint public base_price;
    uint public price_factor;

    // Owner issuance fraction = % of tokens assigned to owner from the total supply
    uint public owner_fr;
    uint public owner_fr_dec;

    enum Stages {
        MintDeployed,
        MintSetUp,
        AuctionStarted,
        AuctionEnded,
        MintingActive
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
        require(_auction != 0x0);
        require(_token != 0x0);
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

        // Example (10, 2) means 10%, we cannot have 1000%
        assert(Utils.num_digits(owner_fr) <= owner_fr_dec);
    }

    // When minting is activated (no auction), buyers use this function
    function buy()
        public
        payable
        isValidPayload
        atStage(Stages.MintingActive)
    {

        // calculate the num of newly issued tokens based on the added reserve (sent currency)
        uint num = curveIssuable(supplyAtReserve(), msg.value);
        issue(msg.sender, num);
    }

    // When minting is activated (no auction), token owners use this function to sell tokens
    function sell(uint num)
        public
        atStage(Stages.MintingActive)
    {
        assert(num > 0);
        token.destroy(msg.sender, num);
        msg.sender.transfer(purchaseCost(num));
    }

    // Destroy tokens with no currency transfer
    function burn(uint num)
        public
        atStage(Stages.MintingActive)
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

    // Current reserve from mint and auction
    function totalReserve()
        public
        constant
        returns (uint)
    {
        return SafeMath.add(this.balance, auction.balance);
    }

    // Called from Auction after all the current auction tokens have been issued
    // We can start minting new tokens
    function startMinting()
        public
        isAuction
        atStage(Stages.AuctionEnded)
    {
        stage = Stages.MintingActive;
    }

    // Called from Auction after it has ended;
    // sends all of the Auction's funds to the Mint contract
    function fundsFromAuction()
        public
        payable
        isAuction
        atStage(Stages.MintSetUp)
    {
        stage = Stages.AuctionEnded;
    }

    // Called from Auction.claimTokens(); issues auction tokens to bidders
    function issueFromAuction(address recipient, uint num)
        public
        isAuction
        atStage(Stages.AuctionEnded)
    {
        issue(recipient, num);
    }

    // Curve functions are named as "curveOutputAtInput"

    // Calculate price at a given supply (number of tokens issued)
    // This is the main function that determines the following functions
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

    // Calculate price at a given reserve/balance
    function curvePriceAtReserve(uint _reserve)
        public
        constant
        returns (uint)
    {
        return curvePriceAtSupply(curveSupplyAtReserve(_reserve));
    }

    // Calculate reserve at a given supply;
    // integral with respect to supply of curvePriceAtSupply()
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

    // Calculate supply at a given reserve/balance
    function curveSupplyAtReserve(uint _reserve)
        public
        constant
        returns (uint)
    {
        // Calculate supply from the curveReserveAtSupply quadratic equation
        uint sqrt = Utils.sqrt(
            SafeMath.add(
                base_price**2,
                SafeMath.mul(
                    SafeMath.mul(2, _reserve),
                    price_factor
                )
            )
        );
        uint supply_value = SafeMath.sub(sqrt, base_price) / price_factor;
        return supply_value;
    }

    // Calculate supply based on the price of 1 token; derived from curvePriceAtSupply
    function curveSupplyAtPrice(uint _price)
        public
        constant
        returns (uint)
    {
        assert(_price >= base_price);
        return SafeMath.sub(_price, base_price) / price_factor;
    }

    // Calculate reserve based on the price of 1 token
    function curveReserveAtPrice(uint _price)
        public
        constant
        returns (uint)
    {
        assert(_price >= 0);
        return curveReserveAtSupply(curveSupplyAtPrice(_price));
    }

    // Calculate cost for a number of tokens at a given supply
    // This can be named as curveAddedReserveAtAddedSupply,
    // cost_value = potentially added reserve; _num = potentially added supply
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
    // This can be named as curveAddedSupplyAtAddedReserve
    // added_reserve = amount of currency that a buyer is willing to pay
    function curveIssuable(uint _supply, uint added_reserve)
        public
        constant
        returns (uint)
    {
        // Get reserve at the provided supply
        uint reserve_value = curveReserveAtSupply(_supply);

        // Calculate total number to tokens that we get for the entire reserve // (including the amount payable by the buyer)
        uint total_supply = curveSupplyAtReserve(SafeMath.add(reserve_value, added_reserve));

        // Subtract the original supply from the total supply
        uint issued_tokens = SafeMath.sub(total_supply, _supply);

        return issued_tokens;
    }

    // Calculate market value for a certain supply
    function curveMarketCapAtSupply(uint _supply)
        public
        constant
        returns (uint)
    {
        // Price from the price-supply curve function * total number of tokens issued
        return SafeMath.mul(curvePriceAtSupply(_supply), _supply);
    }

    function curveSupplyAtMarketCap(uint market_cap)
        public
        constant
        returns (uint)
    {
        // Calculate supply from the curveMarketCapAtSupply quadratic equation
        uint sqrt = Utils.sqrt(
            SafeMath.add(
                base_price**2,
                SafeMath.mul(
                    SafeMath.mul(4, market_cap),
                    price_factor
                )
            )
        );
        uint supply_value = SafeMath.div(
            SafeMath.sub(sqrt, base_price),
            SafeMath.mul(2, price_factor)
        );
        return supply_value;
    }

    // Get supply at current reserve/balance (+auction.balance)
    function supplyAtReserve()
        public
        constant
        returns (uint)
    {
        return curveSupplyAtReserve(totalReserve());
    }

    // Get marketCap for the actual issued supply
    function marketCap()
        public
        constant
        returns (uint)
    {
        // Current sale cost of 1 token * actual supply
        return SafeMath.mul(ask(), token.totalSupply());
    }

    // Current sale cost of 1 token
    function ask()
        public
        constant
        returns (uint)
    {
        return saleCost(1);
    }

    // Get sale cost for a number of tokens, based on the supply calculated at the current reserve
    // Also take into consideration the owner's issuance fraction
    // This sets the ceiling price
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

    // Get the purchase cost of a number of tokens = the price at which the owner buys back tokens from the market
    // This sets the floor price
    function purchaseCost(uint _num)
        public
        constant
        returns (uint)
    {
        if(totalSupply() == 0) {
            return 0;
        }

        assert(_num <= totalSupply());
        uint purchase_cost = SafeMath.mul(totalReserve(), _num) / totalSupply();
        return purchase_cost;
    }

    // Calculate project valuation
    function valuation()
        public
        constant
        returns (uint)
    {
        uint val = SafeMath.max256(
            0,
            SafeMath.sub(marketCap(), totalReserve())
        );
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
        require(stage == Stages.MintSetUp || stage == Stages.MintingActive);
        uint owner_num = ownerFraction(num);
        uint recipient_num = SafeMath.sub(num, owner_num);

        token.issue(recipient, recipient_num);
        token.issue(owner, owner_num);

        return recipient_num;
    }
}
