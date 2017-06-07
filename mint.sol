pragma solidity 0.4.11;
import "RaidenToken.sol";

// TODO: add interface for auction and token

contract Mint {

    /* Events */

    event MintingRightTransferred(address indexed from, address indexed to);

    /* Data structures */

    struct MintingRight {
        uint startTime;
        uint endTime;
        uint total;
        uint issued;
    }

    mapping (address => MintingRight) minters;
    address owner;
    address mintingRightsGranter;
    RaidenToken token;
    uint public maxMintable;
    uint public totalMinted;
    uint public totalMintingRightsGranted;

    /* Enums */

    enum Stages {
        MintDeployed,
        MintSetUp,
        CollateralProvided
    }

    Stages public stage;

    /* Modifiers */

    modifier atStage(Stages _stage) {
        require(stage == _stage);
        _;
    }

    modifier isValidPayload() {
        require(msg.data.length == 4 || msg.data.length == 36);
        _;
    }

    /*  Public functions */

     function Mint(uint _maxMintable) public {
        owner = msg.sender;
        mintingRightsGranter = msg.sender; // changed with setup
        maxMintable = _maxMintable;
        stage = Stages.MintDeployed;
     }


    /// @dev Setup function sets external contracts' addresses.
    function setup(address _token, address _mintingRightsGranter)
        public
        atStage(Stages.MintDeployed)
    {
        require(msg.sender == owner);

        // register token
        require(_token != 0x0);
        require(RaidenToken(_token).maxSupply() == RaidenToken(_token).totalSupply() + maxMintable);

        token = RaidenToken(_token);

        // register mintingRightsGranter
        require(_mintingRightsGranter != 0x0);

        mintingRightsGranter = _mintingRightsGranter;

        stage = Stages.MintSetUp;
        require(address(token) == _token);
        require(mintingRightsGranter == _mintingRightsGranter);
        require(stage == Stages.MintSetUp);
    }

    function isReady() public constant atStage(Stages.MintSetUp) returns (bool) {
        return true;
    }

    // forwards collateral to the token
    function addCollateral()
        public
        payable
        atStage(Stages.MintSetUp)
        returns (bool)
    {
        require(msg.sender == mintingRightsGranter);
        require(token.addCollateral.value(this.balance)()); // FIXME double check

        return true;
    }

    // owner can register minting rights before calling Mint.setup
    function registerMintingRight(address eligible, uint num, uint startTime, uint endTime)
        public
        returns (bool)
    {
        require(msg.sender == mintingRightsGranter);
        require((stage == Stages.MintDeployed && msg.sender == owner) ||
                (stage == Stages.MintSetUp && msg.sender != owner));
        require(minters[eligible].total == 0);
        require(startTime < endTime);
        require(totalMintingRightsGranted + num <= maxMintable);

        minters[eligible] = MintingRight({startTime: startTime,
                                          endTime: endTime,
                                          total: num,
                                          issued: 0});
        totalMintingRightsGranted += num;
        assert(minters[eligible].total = num);
        return true;
    }

    // FIXME, can we return structs to calling contracts?
    function getMintingRight(address eligible)
        public
        constant
        returns (uint[] values)
    {
        MintingRight mr = minters[eligible];
        return (mr.startTime, mr.endTime, mr.total, mr.issued)
    }


    function transferMintingRight(address _eligible)
        public
        isValidPayload
        atStage(Stages.CollateralProvided)
        returns (bool)
    {
        require(minters[msg.sender].total > 0);
        if (minters[_eligible].total > 0) {
            // can only be added if matching minting period
            require(minters[msg.sender].startTime == minters[_eligible].startTime);
            require(minters[msg.sender].endTime == minters[_eligible].endTime);
            minters[_eligible].total += minters[msg.sender].total;
            minters[_eligible].issued += minters[msg.sender].issued;
        } else {
            minters[_eligible] = minters[msg.sender];
        }
        minters[msg.sender] = 0; // FIXME double check
        MintingRightTransferred(msg.sender, _eligible);
        assert(minters[msg.sender].total == 0);
        return true;
    }

    // calc the max mintable amount for account
    function mintable(address account)
        public
        atStage(Stages.CollateralProvided)
        returns (uint)
    {
        uint elapsed;
        MintingRight minter = minters[account];
        if (!minter.has_rights || now < minter.startTime) {
            return 0;
        }
        // calc max mintable
        uint period = minter.endTime - minter.startTime;

        // get min(now - minter.startTime, period)
        if (now - minter.startTime <= period) {
            elapsed = now - minter.startTime;
        } else {
            elapsed = period;
        }
        uint mintableByNow = minter.total * elapsed / period;

        return mintableByNow - minter.issued;
    }

    // note: anyone can call mint
    function mint(uint num, address account)
        public
        atStage(Stages.CollateralProvided)
    {
        require(num > 0);
        require(num <= mintable(account));

        MintingRight minter = minters[account];
        minter.issued += num;
        totalMinted += num;
        require(RaidenToken(token).mint(account, num));

        require(minter.issued <= minter.total);
        require(totalMinted <= totalMintingRightsGranted);
        require(totalMinted <= maxMintable);
    }
}
