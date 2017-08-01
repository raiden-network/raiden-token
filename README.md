# Continous Token

## Smart Contracts, Unittests and Infrastructure.

### Installation

#### Prerequisites

 * Python 3.6
 * [pip](https://pip.pypa.io/en/stable/)

#### Setup

 * pip install -r requirements.txt

#### Usage

 * populus compile
 * pytest
 * populus deploy

#### Testing

 * If testing with Populus TesterChain

 ```
pytest tests_simple -p no:warnings -s
 ```
 * Easy deployment on a testnet

 ```
python deploy.py
 ```

For deployment on Ropsten, connect to the chain and change the `populus.json` settings for `ropsten` with your `default_account` and `ipc_path`.

```
"web3": {
  "eth": {
    "default_account": "0xbb5aeb01acf5b75bc36ec01f5137dd2728fbe983"
  },
  "provider": {
    "class": "web3.providers.ipc.IPCProvider",
    "settings": {
      "ipc_path": "/Users/user/Library/Ethereum/testnet/geth.ipc"
    }
  }
}
```

## Web App

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
