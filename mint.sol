pragma solidity 0.4.11;


/// @title Abstract token contract - Functions to be implemented by token contracts.
contract Token {
    function maxSupply() constant returns (uint256 supply) {}
    function totalSupply() constant returns (uint256) {}
    function addCollateral() payable returns (bool) {}
    function mint(address receiver, uint num) returns (bool) {}
} // FIXME: is it required to specify the complete interface or only the required parts?

contract Mint {

    event MintingRightTransferred(address indexed from, address indexed to);

    /*
     *  Data structures
     */

    struct MintingRight {
        uint startTime;
        uint endTime;
        uint total;
        uint issued;
        bool has_rights;
    }

    mapping (address => MintingRight) minters;
    address owner;
    address mintingRightsGranter;
    Token token;
    uint public maxMintable;
    uint public totalMinted;
    uint public totalMintingRightsGranted;


    enum Stages {
        MintDeployed,
        MintSetUp,
        CollateralProvided
    }

    Stages public stage;

    /*
     *  Modifiers
     */
    modifier atStage(Stages _stage) {
        assert(stage == _stage);
        _;
    }

    modifier isValidPayload() {
        assert(msg.data.length == 4 || msg.data.length == 36);
        _;
    }
    /*
     *  Public functions
     */


     function Mint(uint _maxMintable)
        public
     {
        owner = msg.sender;
        mintingRightsGranter = msg.sender; // changed with setup
        maxMintable = _maxMintable;
        stage = Stages.MintDeployed;
     }


    /// @dev Setup function sets external contracts' addresses.
    /// @param _token Raiden token address.
    function setup(address _token, address _mintingRightsGranter)
        public
        atStage(Stages.MintDeployed)
    {
        assert(msg.sender == owner);
        // register token
        assert(_token != 0x0);
        assert(Token(_token).maxSupply() == Token(_token).totalSupply() + maxMintable);
        // register mintingRightsGranter
        assert(_mintingRightsGranter != 0x0);
        mintingRightsGranter = _mintingRightsGranter;
        stage = Stages.MintSetUp;
    }

    function isReady()
        public
        constant
        atStage(Stages.MintSetUp)
        returns (bool)
    {
        return true;
    }

    // forwards collateral to the token
    function addCollateral()
        public
        payable
        atStage(Stages.MintSetUp)
        returns (bool)
    {
        assert(msg.sender == mintingRightsGranter);
        assert(token.addCollateral.value(this.balance)()); // FIXME double check
        return true;
    }

    // owner can register minting rights before calling Mint.setup
    function registerMintingRight(address eligible, uint num, uint startTime, uint endTime)
        public
        returns (bool)
    {
        assert(msg.sender == mintingRightsGranter);
        assert((stage == Stages.MintDeployed && msg.sender == owner) ||
               (stage == Stages.MintSetUp && msg.sender != owner));
        assert(!minters[eligible].has_rights);
        assert(startTime < endTime);
        minters[eligible] = MintingRight({startTime: startTime,
                                          endTime: endTime,
                                          total: num,
                                          issued: 0,
                                          has_rights: true});
        totalMintingRightsGranted += num;
        assert(totalMintingRightsGranted <= maxMintable);
        return true;
    }

    function transferMintingRight(address _eligible)
        public
        isValidPayload
        atStage(Stages.CollateralProvided)
        returns (bool)
    {
        require(minters[msg.sender].has_rights);
        minters[_eligible] = minters[msg.sender];
        minters[msg.sender] = MintingRight(0, 0, 0, 0, false);
        MintingRightTransferred(msg.sender, _eligible);
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
        if(!minter.has_rights || now < minter.startTime)
            return 0;
        // calc max mintable
        uint period = minter.endTime - minter.startTime;
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
        require(num>0);
        MintingRight minter = minters[account];
        assert(num <= mintable(account));
        minter.issued += num;
        totalMinted += num;
        assert(Token(token).mint(account, num));
        assert(minter.issued <= minter.total);
        assert(totalMinted <= totalMintingRightsGranted);
        assert(totalMinted <= maxMintable);
    }
}
