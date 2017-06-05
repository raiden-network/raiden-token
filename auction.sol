pragma solidity 0.4.11;


/// @title Abstract Mint contract - Functions to be implemented by Mint contracts.
/// FIXME: is it necessary to provide the full interface?

contract Mint {
    function registerMintingRight(address eligible, uint num, uint startTime, uint endTime) returns (bool);
    function mintable(address account) returns (uint);
    function maxMintable() returns (uint);
    function isReady() returns (bool);
    function addCollateral() returns (bool);
}


/// @title Dutch auction contract - distribution of Raiden token Minting rights using an auction
/// @author Heiko, also credits to team Gnosis!
/// This is a variation of the Gnosis model. The price and number of mintable tokens are fixed.
/// Bidders bid for mining rights and compete on the dimension of the their max acceptable minting period.
/// The result of the auctinon are minting rights.
contract DutchAuction {

    /*
     *  Events
     */
    event BidSubmission(address indexed sender, uint256 amount);

    /*
     *  Storage
     */
    Token public token;
    Mint public mint;
    address public owner;
    uint public maxTokensAvailable;
    uint public waitingPeriod;
    uint public collateralCeiling; // max total accepted ETH collateral
    uint public collateralFactor; // tokens mintable per collateral (wei), i.e. 1/price
    uint public minCollateralPerBidder; // minimum collateral a bidder must offer
    uint public maxCollateralFractionPerBidder; // limits the number of tokens a bidder can have
    uint public totalCollateralReceived;
    uint public mintingPeriodFactor;
    uint public mintingPeriodDevisorConstant;
    uint public finalMintingPeriod; // result of the auction is a
    uint public startBlock; // block the auction starts
    uint public endTime; // time the auction ends at latest

    mapping (address => uint) public bids;
    mapping (address => bool) public bidders;

    /*
     *  Enums
     */
    enum Stages {
        AuctionDeployed,
        AuctionSetUp,
        AuctionStarted,
        AuctionEnded,
        TradingStarted
    }
    Stages public stage;


    /*
     *  Modifiers
     */
    modifier atStage(Stages _stage) {
        assert(stage == _stage);
        _;
    }

    modifier isOwner() {
        assert(msg.sender == owner);
        _;
    }

    modifier isValidPayload() {
        assert(msg.data.length == 4 || msg.data.length == 36);
        _;
    }

    modifier timedTransitions() {
        if (stage == Stages.AuctionStarted && (now > endTime || totalCollateralReceived == collateralCeiling))
            finalizeAuction();
        if (stage == Stages.AuctionEnded && now > endTime + waitingPeriod)
            stage = Stages.TradingStarted;
        _;
    }

    /*
     *  Public functions
     */
    /// @dev Contract constructor function sets owner.
    /// @param _collateralCeiling Auction collateralCeiling.
    /// @param _collateralFactor Auction price factor.
    function DutchAuction(uint _collateralCeiling,
                          uint _collateralFactor,
                          uint _maxTokensAvailable
                          uint _minCollateralPerBidder,
                          uint _maxCollateralFractionPercentPerBidder,
                          uint _mintingPeriodFactor,
                          uint _mintingPeriodDevisorConstant,
                          uint _waitingPeriod)
        public
    {
        owner = msg.sender;
        assert(_collateralCeiling && _collateralFactor);
        collateralCeiling = _collateralCeiling;
        collateralFactor = _collateralFactor;
        assert(_maxTokensAvailable);
        maxTokensAvailable = _maxTokensAvailable;
        assert(_minCollateralPerBidder)
        minCollateralPerBidder = _minCollateralPerBidder;
        assert(0 < _maxCollateralFractionPerBidder <=100);
        maxCollateralFractionPerBidder = _maxCollateralFractionPercentPerBidder;
        assert(_mintingPeriodFactor && _mintingPeriodDevisorConstant);
        mintingPeriodFactor = _mintingPeriodFactor;
        mintingPeriodDevisorConstant = _mintingPeriodDevisorConstant;
        waitingPeriod = _waitingPeriod;
        stage = Stages.AuctionDeployed;
    }

    /// @dev call to whitelist bidders
    function registerEligibleBidders(address[] _bidders)
        public
        isOwner
        atStage(Stages.AuctionDeployed)
    {
        for (uint i=0; i<_bidders.length; i++) {
            assert(_bidders[i] != 0);
            bidders[_bidders[i]] = true;
        }
    }

    /// @dev Setup function sets external contracts' addresses.
    /// @param _token the token address.
    function setup(address _mint)
        public
        isOwner
        atStage(Stages.AuctionDeployed)
    {
        // register mint
        assert(_mint);
        mint = Mint(_mint);
        assert(mint.isReady());
        assert(mint.maxMintable() - mint.totalMintingRightsGranted() >= maxTokensAvailable);
        stage = Stages.AuctionSetUp;
    }



    /// @dev Changes auction collateralCeiling and start price factor before auction is started.
    /// @param _collateralCeiling Updated auction collateralCeiling.
    /// @param _collateralFactor Updated start price factor.
    function changeSettings(uint _collateralCeiling, uint _collateralFactor)
        public
        idOwner
        atStage(Stages.AuctionSetUp)
    {
        collateralCeiling = _collateralCeiling;
        collateralFactor = _collateralFactor;
    }

    /// @dev Starts auction and sets startBlock.
    function startAuction()
        public
        isOwner
        atStage(Stages.AuctionSetUp)
    {
        stage = Stages.AuctionStarted;
        startBlock = block.number;
    }


    /// @dev Returns correct stage, even if a function with timedTransitions modifier has not yet been called yet.
    /// @return Returns current auction stage.
    function updateStage()
        public
        timedTransitions
        returns (Stages)
    {
        return stage;
    }

    /// @dev Allows to send a bid to the auction.
    /// @param bidder Bid will be assigned to this address if set.
    function bid(address bidder)
        public
        payable
        isValidPayload
        timedTransitions
        atStage(Stages.AuctionStarted)
        returns (uint amount)
    {
        // If a bid is done on behalf of a user via ShapeShift, the bidder address is set.
        if (bidder == 0)
            bidder = msg.sender;
        // check if whitelisted
        assert(bidders[bidder]);

        // enforce percentage per bidder limit
        uint maxWeiAccepted = collateralCeiling * maxCollateralFractionPercentPerBidder / 100;
        maxWeiAccepted -= bids[bidder]; // take in to account previously sent wei

        // enforce total collateral limit
        maxWeiAccepted = min(maxWeiAccepted, collateralCeiling - totalCollateralReceived);

        uint numWei = msg.value;

        // refund non acceptable wei
        if (numWei > maxWeiAccepted) {
            numWei = maxWeiAccepted;
            // Send change back to bidder address. In case of a ShapeShift bid the user receives the change back directly.
            assert(msg.value >= numWei);
            uint refund = msg.value - numWei
            assert(bidder.send(refund));
        }

        // register bid
        assert(numWei>0);
        bids[bidder] += numWei;
        BidSubmission(bidder, numWei);

        // enforce minimum required collateral per bidder, while allowing to add amounts later
        assert(bids[bidder] > minCollateralPerBidder);
        totalCollateralReceived += numWei;
        assert(totalCollateralReceived <= collateralCeiling);
        assert(totalCollateralReceived * collateralFactor <= maxTokensAvailable);

        // finalize if full
        if (totalCollateralReceived == collateralCeiling)
            // When maxWei is equal to the big numWei the auction is ended and finalizeAuction is triggered.
            finalizeAuction();
    }


    // mintingPeriodFactor: 10_000_000, mintingPeriodDevisorConstant: 1_000
    // starts with 27yrs, 4.5yrs @24hs, 2.4yrs @48hrs, 1.5yrs @72hrs
    function calcMintingPeriod(uint elapsedBlocks)
        constant
        public
        returns (uint)
        {
            return mintingPeriodFactor / (elapsedBlocks + mintingPeriodDevisorConstant);
        }

    function currentMintingPeriod()
        constant
        public
        atStage(Stage.AuctionStarted)
        returns (uint)
        {
            return calcMintingPeriod(block.number - startBlock);
        }


    function finalizeAuction()
        private
    {
        stage = Stages.AuctionEnded;
        endTime = now;

        // register mintingPeriod for all successful bidders
        uint elapsed = block.number - startBlock;
        finalMintingPeriod = calcMintingPeriod(elapsed);

        // Transfer funding to collateralize the token
        assert(mint.addCollateral.value(this.value)()); // FIXME double check
    }

    /// @dev registers minting rights for bidder after auction with the Mint
    /// @param receiver MintingRighhts will be assigned to this address if set
    function registerMintingRights(address receiver)
        public
        isValidPayload
        timedTransitions
        atStage(Stages.TradingStarted)
    {
        if (receiver == 0)
            receiver = msg.sender;
        uint tokenCount = bids[receiver] * collateralFactor;
        assert(tokenCount>0);
        bids[receiver] = 0;
        assert(mint.registerMintingRight(receiver, tokenCount, endTime, endTime + finalMintingPeriod));
    }

}
