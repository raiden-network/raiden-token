pragma solidity 0.4.11;
import "token.sol";
import "mint.sol";

/// @title Raiden token contract
/// @author Heiko Hees

// Allow to tokenize MintingRights and make them tradable
//
// Mechanics:
// Contract which owns and tokenizes minting rights, i.e. allows to trade tokens that will be mintable in the future.
// In order to be fungible all tokenized MintingRights need to have the same start and maturity date.
// One future token represents the right to receive one original token at the maturity date
// the contract mints tokens (if called to do so) and keeps them until the minting period ended.
//
// 1) Transfer minting rights to the contract
// 2) get future tokens equivalent to the number of not minted tokens
// 3) at the maturity date the tokens can be claimed by destroying the future
// 4) future tokens can be freely transferred (i.e. traded)

contract RaidenFuturesToken is StandardToken {

    /*  Token meta data */

    string constant public name = "Raiden Token Future";
    string constant public symbol = "RDNF";
    uint constant public decimals = 24;  // ETH has 18
    Token public token;
    Mint public mint;
    uint startTime;
    uint endTime;

    /* Events */

    event Destroyed(address indexed receiver, uint num, uint _totalSupply);
    event Issued(address indexed receiver, uint num, uint _totalSupply);

    /*  Public functions */

    /// @dev Contract constructor function sets the token and mint contract address plus minting period
    function RaidenFuturesToken(address _token, address _mint, uint _startTime, uint _endTime)
        public
    {
        token = _token;
        mint = _mint;
        startTime = _startTime;
        endTime = _endTime;
    }

    // how many tokens an address can mint now and in the future in total
    function totalMintable(address _account)
        public
        constant
    {
        uint[] mr = mint.getMintingRight(_account);
        require(mr[0] == startTime && mr[1] == endTime); // require compatible minting periods
        return mr[2] - mr[3]; // total - issued
    }

    // convert minting rights to futures
    function issue()
        public
    {
        require(totalMintable(msg.sender) > 0); // implicitly requires compatible minting periods
        // transfer rights to this contract
        uint mintable_before = totalMintable(this.address);
        // transfer minting rights to this contract
        // note: would not fail for the first call if minting periods don't match!
        require(mint.delegatecall(bytes4(sha3("transferMintingRight(address)"), this.address)); // FIXME
        uint mintable_after = totalMintable(this.address);
        uint newly_issued = mintable_after - mintable_before;
        require(newly_issued >0);
        totalSupply += newly_issued;
        balances[msg.sender] += newly_issued;
        assert(totalSupply == mintable_after);
        assert(totalSupply <= token.totalSupply());
        Issued(msg.sender, newly_issued, totalSupply);
    }

    // anyone can call at any time. helpful to update the totalSupply of token
    function mintOutstandingTokens()
        public
        returns (uint)
    {
        // mint all minable tokens
        uint mintable = mint.mintable(this.address);
        if (mintable) {
            assert(mint.mint(mintable, this.address));
            assert(totalSupply == token.balanceOf(this.address));
        }
        return mintable;
    }


    // after endTime, the futures can be converted to their respective Tokens
    function destroy()
        public
    {
        uint num = balances[msg.sender];
        require(num>0);
        require(now >= endTime);
        mintOutstandingTokens();
        totalSupply -= num;
        balances[msg.sender] = 0;
        assert(token.transfer(msg.sender, num));
        assert(totalSupply == token.balanceOf(this.address));
        Destroyed(msg.sender, num, totalSupply);
    }
}
