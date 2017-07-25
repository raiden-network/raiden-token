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

#### Testing

 * If testing with Populus TesterChain

 ```
pytest tests_simple -p no:warnings -s
 ```
 * Easy deployment on a testnet

 ```
python deploy.py
 ```
