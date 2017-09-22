pragma solidity ^0.4.11;

import './token.sol';

/// @title Dutch auction contract - distribution of tokens using an auction.
contract DutchAuction {
    /*
     * Auction for the TKN Token.
     *
     * Terminology:
     * 1 token unit = Tei
     * 1 token = TKN = Tei * multiplier
     * multiplier set from token's number of decimals (i.e. 10**decimals)
     */

    /*
     * Storage
     */

    CustomToken public token;
    address public owner;
    address public wallet;

    // Price function parameters
    uint public price_factor;
    uint public price_const;

    // For calculating elapsed time for price
    uint public start_time;
    uint public end_time;
    uint public start_block;

    // Keep track of all ETH received in the bids
    uint public received_ether;

    // Keep track of funds claimed after auction has ended
    uint public funds_claimed;

    // Total number of Tei (TKN * multiplier) that will be auctioned
    uint public multiplier;
    uint public tokens_auctioned;

    // Wei per TKN (Tei * multiplier)
    uint public final_price;

    mapping (address => uint) public bids;

    Stages public stage;

    // TODO - remove after testing
    uint rounding_error_tokens;

    /*
     * Enums
     */
    enum Stages {
        AuctionDeployed,
        AuctionSetUp,
        AuctionStarted,
        AuctionEnded,
        TokensDistributed
    }

    /*
     * Modifiers
     */
    modifier atStage(Stages _stage) {
        require(stage == _stage);
        _;
    }

    modifier isOwner() {
        require(msg.sender == owner);
        _;
    }

    modifier isValidPayload() {
        require(msg.data.length == 0 || msg.data.length == 4 || msg.data.length == 36);
        _;
    }

    /*
     * Events
     */

    event Deployed(
        address indexed _auction,
        uint indexed _price_factor,
        uint indexed _price_const
    );
    event Setup();
    event SettingsChanged(uint indexed _price_factor, uint indexed _price_const);
    event AuctionStarted(uint indexed _start_time, uint indexed _block_number);
    event BidSubmission(
        address indexed _sender,
        uint indexed _amount,
        uint indexed _missing_funds
    );
    event ClaimedTokens(address indexed _recipient, uint indexed _sent_amount);
    event AuctionEnded(uint indexed _final_price);
    event TokensDistributed();

    /*
     * Public functions
     */

    /// @dev Contract constructor function sets price factor and constant for
    /// calculating the Dutch Auction price.
    /// @param _wallet Wallet address to which all contributed ETH will be forwarded.
    /// @param _price_factor Auction price factor.
    /// @param _price_const Auction price divisor constant.
    function DutchAuction(address _wallet, uint _price_factor, uint _price_const) public {
        require(_wallet != 0x0);
        wallet = _wallet;

        owner = msg.sender;
        stage = Stages.AuctionDeployed;
        Deployed(this, price_factor, price_const);
        changeSettings(_price_factor, _price_const);
    }

    /// @dev Fallback function for the contract, which calls bid() if the auction has started.
    function () public payable atStage(Stages.AuctionStarted) {
        bid(msg.sender);
    }

    /// @notice Set `_token` as the token address to be used in the auction.
    /// @dev Setup function sets external contracts addresses.
    /// @param _token Token address.
    function setup(address _token) public isOwner atStage(Stages.AuctionDeployed) {
        require(_token != 0x0);
        token = CustomToken(_token);
        require(token.owner() == owner);
        require(token.auction_address() == address(this));

        // Get number of Tei (TKN * multiplier) to be auctioned from token auction balance
        tokens_auctioned = token.balanceOf(this);

        // Set number of tokens multiplier from token decimals
        multiplier = 10**uint(token.decimals());

        stage = Stages.AuctionSetUp;
        Setup();
    }

    /// @notice Set `_price_factor` and `_price_const` as the new price factor
    /// and price divisor constant.
    /// @dev Changes auction start price factor before auction is started.
    /// @param _price_factor Updated price factor.
    /// @param _price_const Updated price divisor constant.
    function changeSettings(uint _price_factor, uint _price_const) public isOwner {
        require(stage == Stages.AuctionDeployed || stage == Stages.AuctionSetUp);
        require(_price_factor > 0);
        require(_price_const > 0);

        price_factor = _price_factor;
        price_const = _price_const;
        SettingsChanged(price_factor, price_const);
    }

    /// @notice Start the auction.
    /// @dev Starts auction and sets start_time.
    function startAuction() public isOwner atStage(Stages.AuctionSetUp) {
        stage = Stages.AuctionStarted;
        start_time = now;
        start_block = block.number;
        AuctionStarted(start_time, start_block);
    }

    /// @notice Finalize the auction - sets the final price and changes the auction
    /// stage after no bids are allowed anymore.
    /// @dev Finalize auction and set the final token price.
    function finalizeAuction() public atStage(Stages.AuctionStarted)
    {
        // Missing funds should be 0 at this point
        uint missing_funds = missingFundsToEndAuction();
        require(missing_funds == 0);

        // Calculate the final price WEI / TKN = WEI / (Tei / multiplier)
        final_price = multiplier * received_ether / tokens_auctioned;

        end_time = now;
        stage = Stages.AuctionEnded;
        AuctionEnded(final_price);

        assert(final_price > 0);
    }

    /// --------------------------------- Auction Functions ------------------

    /// @notice Send `msg.value` WEI to the auction from the `msg.sender` account.
    /// @dev Allows to send a bid to the auction.
    function bid() public payable atStage(Stages.AuctionStarted) {
        bid(msg.sender);
    }

    /// @notice Send `msg.value` WEI to the auction from the `receiver` account.
    /// @dev Allows to send a bid to the auction.
    /// @param receiver Bidder account address.
    function bid(address receiver)
        public
        payable
        isValidPayload
        atStage(Stages.AuctionStarted)
    {
        require(receiver != 0x0);
        require(msg.value > 0);
        require(bids[receiver] + msg.value >= msg.value);

        uint pre_receiver_funds = bids[receiver];

        // Missing funds without the current bid value
        uint missing_funds = missingFundsToEndAuction();

        // We only allow bid values less than the missing funds to end the auction value.
        require(msg.value <= missing_funds);

        bids[receiver] += msg.value;
        received_ether += msg.value;

        // Send bid amount to wallet
        wallet.transfer(msg.value);

        BidSubmission(receiver, msg.value, missing_funds);

        assert(bids[receiver] == pre_receiver_funds + msg.value);
        assert(received_ether >= msg.value);
    }

    /// @notice Claim auction tokens for `msg.sender` after the auction has ended.
    /// @dev Claims tokens for bidder after auction. To be used if tokens can be claimed by bidders, individually.
    function claimTokens() public atStage(Stages.AuctionEnded) {
        claimTokens(msg.sender);
    }

    /// @notice Claim auction tokens for `receiver` after the auction has ended.
    /// @dev Claims tokens for bidder after auction.
    /// @param receiver Tokens will be assigned to this address if set.
    function claimTokens(address receiver)
        public
        isValidPayload
        atStage(Stages.AuctionEnded)
    {
        require(receiver != 0x0);
        require(bids[receiver] > 0);

        // Number of Tei = bidded_wei / wei_per_TKN * multiplier
        uint num = multiplier * bids[receiver] / final_price;

        // Update funds claimed with full bidded amount
        // rounding errors are included to not block the contract
        funds_claimed += bids[receiver];

        // Set receiver bid to 0 before assigning tokens
        bids[receiver] = 0;

        require(token.transfer(receiver, num));

        ClaimedTokens(receiver, num);

        // Test for a correct claimed tokens calculation
        /* TODO remove this after testing */
        uint auction_unclaimed_tokens = token.balanceOf(this);

        uint unclaimed_tokens = (received_ether - funds_claimed) * multiplier / final_price;
        unclaimed_tokens += rounding_error_tokens;

        if (auction_unclaimed_tokens != unclaimed_tokens) {
            rounding_error_tokens += 1;
            unclaimed_tokens += 1;
        }
        assert(auction_unclaimed_tokens == unclaimed_tokens);
        /* End of removable test */

        // After the last tokens are claimed, we send the auction balance to the owner
        // and change the auction stage
        if (funds_claimed == received_ether) {
            stage = Stages.TokensDistributed;
            TokensDistributed();
        }

        assert(token.balanceOf(receiver) >= num);
        assert(bids[receiver] == 0);
    }

    /*
     *  Private functions
     */

    /// @dev Calculates the token price (WEI / TKN) at the current timestamp
    /// during the auction; elapsed time = 0 before auction starts.
    /// @dev At AuctionDeployed the price is 1, because multiplier is 0
    /// @return Returns the token price - Wei per TKN.
    function calcTokenPrice() constant private returns (uint) {
        uint elapsed;
        if (stage == Stages.AuctionStarted) {
            elapsed = now - start_time;
        }
        return multiplier * price_factor / (elapsed + price_const) + 1;
    }

    /// --------------------------------- Price Functions ----------------------

    /// @notice Get the TKN price in WEI during the auction, at the moment of
    /// calling this method. Returns `0` if auction has ended.
    /// @dev Calculates current token price.
    /// @return Returns num Wei per TKN (multiplier * Tei).
    function price() public constant returns (uint) {
        if (stage == Stages.AuctionEnded ||
            stage == Stages.TokensDistributed) {
            return 0;
        }
        return calcTokenPrice();
    }

    /// @notice Get the missing funds needed to end the auction,
    /// calculated at the current TKN price.
    /// @dev The missing funds amount necessary to end the auction at the current price.
    /// @return Returns the missing funds amount.
    function missingFundsToEndAuction() constant public returns (uint) {
        uint funds_at_price = tokens_auctioned * price() / multiplier;
        if (funds_at_price < received_ether) {
            return 0;
        }
        return funds_at_price - received_ether;
    }
}
