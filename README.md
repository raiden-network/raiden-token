# Continous Token

Smart Contracts, Unittests and Infrastructure.

## Installation

### Prerequisites

 * Python 3.6
 * [pip](https://pip.pypa.io/en/stable/)

### Setup

 * pip install -r requirements.txt

### Usage

 * populus compile
 * pytest
 * populus deploy

#### Testing recommendations

 * If testing with Populus TesterChain

 ```
 pytest tests_simple -p no:warnings -s
 ```

- not enough accounts & balance for token decimals = 18, so:
    - set `multiplier = 10**10` in `tests_simple/test_fixtures.py`
    - set `uint8 constant public decimals = 10;` in `simple_auction/token.sol`
