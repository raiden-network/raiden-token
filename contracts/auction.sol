pragma solidity ^0.4.11;

contract Auction {
    address owner;
    uint factor;
    uint const;
    uint public startBlock;
    uint public endBlock;
    // uint elapsed = 0;

    enum Stages {
        AuctionDeployed,
        AuctionSetUp,
        AuctionStarted,
        AuctionEnded,
        TradingStarted
    }

    Stages public stage;

    modifier isOwner() {
        require(msg.sender == owner);
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

    function Auction(uint _factor, uint _const) {
        factor = _factor;
        const = _const;
        stage = Stages.AuctionDeployed;
    }

    // Simulated supply
    function price_surcharge() returns(uint value) {
        uint elapsed = block.number - startBlock;
        return factor / elapsed + const;
    }

    function startAuction() public isOwner atStage(Stages.AuctionSetUp) {
        stage = Stages.AuctionStarted;
        startBlock = block.number;
    }

    function finalizeAuction() private {
        stage = Stages.AuctionEnded;
        endBlock = now;
    }
}
