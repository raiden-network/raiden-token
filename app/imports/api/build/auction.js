export default Auction = {
    address: '0x3fde1c0aec3731a01de2ba45fa0ea665f8bc49f2',
    transactionHash: '0x4e94dec3a9010b04128560070b7e369ba5e0f7a37453be9df691b49d61786f4d',
    abi: [
      {
        "constant": true,
        "inputs": [],
        "name": "price_const",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [
          {
            "name": "_price_factor",
            "type": "uint256"
          },
          {
            "name": "_price_const",
            "type": "uint256"
          },
          {
            "name": "_final_auction",
            "type": "bool"
          }
        ],
        "name": "changeSettings",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "auctionIsActive",
        "outputs": [
          {
            "name": "",
            "type": "bool"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "received_value",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [
          {
            "name": "_mint",
            "type": "address"
          }
        ],
        "name": "setup",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [],
        "name": "startAuction",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "total_issuance",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "owner",
        "outputs": [
          {
            "name": "",
            "type": "address"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "price",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "endTimestamp",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "missingReserveToEndAuction",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [],
        "name": "order",
        "outputs": [],
        "payable": true,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "stage",
        "outputs": [
          {
            "name": "",
            "type": "uint8"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "auctionMarketCap",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "auctionValuation",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "issued_value",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [
          {
            "name": "recipient",
            "type": "address"
          }
        ],
        "name": "claimTokens",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "price_factor",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [
          {
            "name": "current_reserve",
            "type": "uint256"
          }
        ],
        "name": "missingReserveToEndAuction",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "startTimestamp",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [
          {
            "name": "",
            "type": "address"
          }
        ],
        "name": "bidders",
        "outputs": [
          {
            "name": "",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "function"
      },
      {
        "inputs": [
          {
            "name": "_price_factor",
            "type": "uint256"
          },
          {
            "name": "_price_const",
            "type": "uint256"
          }
        ],
        "payable": false,
        "type": "constructor"
      },
      {
        "payable": true,
        "type": "fallback"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_auction",
            "type": "address"
          },
          {
            "indexed": false,
            "name": "_price_factor",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_price_const",
            "type": "uint256"
          }
        ],
        "name": "Deployed",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_stage",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_mint",
            "type": "address"
          }
        ],
        "name": "Setup",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_stage",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_price_factor",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_price_const",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_final_auction",
            "type": "bool"
          }
        ],
        "name": "SettingsChanged",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_stage",
            "type": "uint256"
          }
        ],
        "name": "AuctionStarted",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_recipient",
            "type": "address"
          },
          {
            "indexed": false,
            "name": "_sent_value",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_accepted_value",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_missing_reserve",
            "type": "uint256"
          }
        ],
        "name": "Ordered",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_recipient",
            "type": "address"
          },
          {
            "indexed": false,
            "name": "_sent_value",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_num",
            "type": "uint256"
          }
        ],
        "name": "ClaimedTokens",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_stage",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_received_value",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_total_issuance",
            "type": "uint256"
          }
        ],
        "name": "AuctionEnded",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_stage",
            "type": "uint256"
          }
        ],
        "name": "AuctionSettled",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_price",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_timestamp",
            "type": "uint256"
          }
        ],
        "name": "AuctionPrice",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_balance",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_missing_reserve",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_timestamp",
            "type": "uint256"
          }
        ],
        "name": "MissingReserve",
        "type": "event"
      }
    ]
}
