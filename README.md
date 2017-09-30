# Raiden Token

## Smart Contracts, Unittests and Infrastructure.

### Installation

#### Prerequisites

 * Python 3.6
 * [pip](https://pip.pypa.io/en/stable/)

#### Setup

 * pip install -r requirements.txt

#### Usage

```sh

# compilation
populus compile

# tests
pytest -p no:warnings -s
pytest tests/test_auction.py -p no:warnings -s

# Recommended:
pip install pytest-xdist
pytest -p no:warnings -s -n NUM_OF_CPUs

```

#### Deployment


##### Chain setup

 * `privtest`
   - start:
   ```
   geth --ipcpath="~/Library/Ethereum/privtest/geth.ipc" --datadir="~/Library/Ethereum/privtest"  --dev  --rpccorsdomain '*'  --rpc  --rpcport 8545 --rpcapi eth,net,web3,personal --unlock 0xf590ee24CbFB67d1ca212e21294f967130909A5a --password ~/password.txt

   # geth console
   # you have to mine yourself: miner.start()
   geth attach ipc:/Users/user/Library/Ethereum/privtest/geth.ipc
   ```

 * `kovan`
   - change default account: [/populus.json#L189](/contracts/populus.json#L189)
   - start https://github.com/paritytech/parity
   ```
   parity --geth --chain kovan --force-ui --reseal-min-period 0 --jsonrpc-cors http://localhost --jsonrpc-apis web3,eth,net,parity,traces,rpc,personal --unlock 0x5601Ea8445A5d96EEeBF89A67C4199FbB7a43Fbb --password ~/password.txt --author 0x5601Ea8445A5d96EEeBF89A67C4199FbB7a43Fbb
   ```
 * `ropsten`
   - change default account: [/contracts/populus.json#L52](/contracts/populus.json#L52)
   - start:
   ```
   geth --testnet --rpc  --rpcport 8545 --unlock 0xbB5AEb01acF5b75bc36eC01f5137Dd2728FbE983 --password ~/password.txt

   ```

 * `rinkeby`
   - https://www.rinkeby.io/ (has a Faucet)
   - change default account: [/contracts/populus.json#L224](/contracts/populus.json#L224)
   - start:
   ```
   # First time
   geth --datadir="~/Library/Ethereum/rinkeby" --rpc --rpcport 8545 init ~/Library/Ethereum/rinkeby.json
   geth --networkid=4 --ipcpath="~/Library/Ethereum/rinkeby/geth.ipc" --datadir="~/Library/Ethereum/rinkeby" --cache=512 --ethstats='yournode:Respect my authoritah!@stats.rinkeby.io' --bootnodes=enode://a24ac7c5484ef4ed0c5eb2d36620ba4e4aa13b8c84684e1b4aab0cebea2ae45cb4d375b77eab56516d34bfbd3c1a833fc51296ff084b770b94fb9028c4d25ccf@52.169.42.101:30303 --rpc --rpcport 8545 --unlock 0xd96b724286c592758de7cbd72c086a8a8605417f --password ~/password.txt

   # use geth console
   geth attach ipc:/Users/user/Library/Ethereum/rinkeby/geth.ipc
   ```



```sh

# Fast deploy on kovan | ropsten | rinkeby | tester | privtest

# Following two calls are quivalent
python -m deploy.deploy_testnet
python -m deploy/deploy_testnet \
    --chain kovan \
    --owner 0x5601Ea8445A5d96EEeBF89A67C4199FbB7a43Fbb  \  # web3.eth.accounts[0]
    --supply 10000000 \
    --price-factor 2 \
    --price-constant 7500 \

# Custom preallocations
python -m deploy.deploy_testnet \
    --prealloc-addresses \ '0xe2e429949e97f2e31cd82facd0a7ae38f65e2f38,0xd1bf222ef7289ae043b723939d86c8a91f3aac3f' \
    --prealloc-amounts '300,600'

```


#### Auction simulation

Simulation will cycle funds, so we don't loose them: owner's account funds the bidder's accounts. When the auction ends, the owner's account receives the auction funds.

```sh

# Simulation options (only when the --simulation flag is set)
    --simulation
    --bidders 10  # number of bidders
    --bids 10  # number of bids
    --price-points 100000000000000000,0,10000000000000000,600  # calculates price_factor & price_constant from 2 price points (wei/TKN, elapsed_seconds)
    --bid-price  # price per TKN in WEI at which the first bid should start
    --bid-interval  # time interval in seconds between bids
    --no-fund   # does not fund the bidder accounts from the owner's

# Testing simulation script locally - tricky,
# because it usually either takes too long or is too expensive
# solution: make Token's decimals = 1 and:
python deploy/deploy_testnet.py --simulation --chain privtest --price-points 1000,0,500,60 --decimals 1 --bid-interval 0 --bidders 4 --no-fund

```


#### Automatic token distribution


```sh

python deploy/distribute.py \
    --chain privtest \
    --distributor 0x8b96503f6b2cefaa83d385fa2cb269999ab4ac9f \
    --distributor-tx 0xc4eaffce4009eb13cd432f3c25d6f5eafb42249d4cd81a6164e83225ad65abee \
    --auction 0x66b14432eaad5956e57ab02316a50705f2dc4f25 \
    --auction-tx 0x989bf8f2cf5bdfdd053c95b4ce711636054f06406df41cd77160b2fad31efe2c \
    --claims 2  # number of addresses to be sent in a transaction (wip)

```

### Solidity coding style

For solidity we generally follow the style guide as shown in the [solidity documentation](http://solidity.readthedocs.io/en/develop/style-guide.html)
with a few notable exceptions:

**Variable Names**

All variable name should be in snake case, just like in python. Function names on the other hand should be mixedCase.
MixedCase is essentially like CamelCase but with the initial letter being a small letter.
This helps us to easily determine which function calls are smart contract calls in the python code side.

```js
function iDoSomething(uint awesome_argument) {
    doSomethingElse();
}
```

**Modifiers in long function declarations**


This is how the solidity documentation suggests it:

```js
function thisFunctionNameIsReallyLong(
    address x,
    address y,
    address z,
)
    public
    onlyowner
    priced
    returns (address)
{
    doSomething();
}
```

This is the minor modification we make in order to make the code more readable when quickly skimming through it.
The thinking here is to easily spot the start of the function's block when skimming and not have the modifiers
appearing as if they are a block on their own due to the hanging parentheses.

```js
function thisFunctionNameIsReallyLong(
    address x,
    address y,
    address z)

    public
    onlyowner
    priced
    returns (address)
{
    doSomething();
}
```


## Web App

Web prototype for testing auction models.


### Installation

#### Prerequisites

 * Meteor 1.5

#### Setup

```
cd app
meteor npm install
```

#### Usage

```
cd app
meteor
```
