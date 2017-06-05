pragma solidity 0.4.11;


/// @title Abstract token contract - Functions to be implemented by token contracts.
contract Token {
    function maxSupply() constant returns (uint256 supply) {}
    function mint(address receiver, uint num) returns (bool) {}
} // FIXME: is it required to specify the complete interface or only the required parts?

contract Mint {

    /*
     *  Data structures
     */

    struct MintingRight {
        uint startTime;
        uint endTime;
        uint total;
        uint issued;
    }

    mapping (address => MintingRight) minters;
    address owner;
    address mintingRightGranter;
    address token;
    uint public maxMintable;
    uint public totalMinted;
    uint public totalMintingRightsGranted;


    enum Stages {
        MintDeployed,
        MintSetUp
    }

    Stages public stage;
    /*
     *  Modifiers
     */
    modifier atStage(Stages _stage) {
        assert(stage == _stage);
        _;
    }

    /*
     *  Public functions
     */


     function Mint(uint _maxMintable)
        public
     {
        owner = msg.sender;
        maxMintable = _maxMintable;
        stage = Stages.MintDeployed;
     }


    /// @dev Setup function sets external contracts' addresses.
    /// @param _token Raiden token address.
    function setup(address _token, address _mintingRightGranter)
        public
        atStage(MintDeployed)
    {
        assert(msg.sender == owner);
        // register token
        assert(_token);
        assert(Token(_token).maxSupply() == token.totalSupply() + maxMintable);
        // register mintingRightGranter
        assert(_mintingRightGranter);
        mintingRightGranter = _mintingRightGranter;
        stage = Stages.MintSetUp;
    }

    function isReady()
        public
        atStage(Stages.MintSetUp)
        returns (bool)
    {
        return True;
    }


    function registerMintingRight(address eligible, uint num, uint startTime, uint endTime)
        public
        atStage(Stages.MintSetUp)
        returns (bool)
    {
        assert(msg.sender == mintingRightGranter);
        assert(!minters[eligible]);
        assert(startTime < endTime);
        minters[eligible] = MintingRight({startTime: startTime,
                                          endTime: endTime,
                                          total: num,
                                          issued: 0});
        totalMintingRightsGranted += num
        assert(totalMintingRightsGranted <= maxMintable);
        return True;
    }

    // calc the max mintable amount for account
    function mintable(address account)
        public
        atStage(Stages.MintSetUp)
        returns (uint)
    {
        MintingRight minter = minters[account];
        if(!minter || now < minter.startTime)
            return 0;
        // calc max mintable
        uint period = minter.endTime - minter.startTime;
        uint elapsed = min(now - minter.startTime, period);
        uint mintableByNow = minter.total * elapsed / period:
        return mintableByNow - minter.issued;
    }


    // note: anyone can call mint
    function mint(uint num, address account)
        public
        atStage(Stages.MintSetUp)
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
