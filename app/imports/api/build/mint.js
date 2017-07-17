export default Mint = {
    //address: '0x6f3380f5ecd9c799e14a47267fbbc62781755ed0',
    address: '0x66bedfcffab61e20a5ca9cc1b8d8bb9eb2544111',
    abi: [
      {
        "constant": true,
        "inputs": [
          {
            "name": "_supply",
            "type": "uint256"
          },
          {
            "name": "added_reserve",
            "type": "uint256"
          }
        ],
        "name": "curveIssuable",
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
            "name": "_value",
            "type": "uint256"
          }
        ],
        "name": "ownerFraction",
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
            "name": "_supply",
            "type": "uint256"
          }
        ],
        "name": "curveReserveAtSupply",
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
            "name": "_price",
            "type": "uint256"
          }
        ],
        "name": "curveReserveAtPrice",
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
        "name": "valuation",
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
        "name": "marketCap",
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
            "name": "_auction",
            "type": "address"
          },
          {
            "name": "_token",
            "type": "address"
          }
        ],
        "name": "setup",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [
          {
            "name": "_price",
            "type": "uint256"
          }
        ],
        "name": "curveSupplyAtPrice",
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
            "name": "_supply",
            "type": "uint256"
          },
          {
            "name": "_num",
            "type": "uint256"
          }
        ],
        "name": "curveCost",
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
            "name": "num",
            "type": "uint256"
          }
        ],
        "name": "burn",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [
          {
            "name": "_supply",
            "type": "uint256"
          }
        ],
        "name": "curveMarketCapAtSupply",
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
        "name": "ask",
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
        "name": "fundsFromAuction",
        "outputs": [],
        "payable": true,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "issuedSupply",
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
            "name": "market_cap",
            "type": "uint256"
          }
        ],
        "name": "curveSupplyAtMarketCap",
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
        "name": "owner_fr_dec",
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
        "name": "startMinting",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [
          {
            "name": "_base_price",
            "type": "uint256"
          },
          {
            "name": "_price_factor",
            "type": "uint256"
          },
          {
            "name": "_owner_fr",
            "type": "uint256"
          },
          {
            "name": "_owner_fr_dec",
            "type": "uint256"
          }
        ],
        "name": "changeSettings",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [
          {
            "name": "_reserve",
            "type": "uint256"
          }
        ],
        "name": "curvePriceAtReserve",
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
            "name": "_reserve",
            "type": "uint256"
          }
        ],
        "name": "curveSupplyAtReserve",
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
        "name": "buy",
        "outputs": [],
        "payable": true,
        "type": "function"
      },
      {
        "constant": false,
        "inputs": [
          {
            "name": "recipient",
            "type": "address"
          },
          {
            "name": "num",
            "type": "uint256"
          }
        ],
        "name": "issueFromAuction",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "supplyAtReserve",
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
        "inputs": [
          {
            "name": "_supply",
            "type": "uint256"
          }
        ],
        "name": "curvePriceAtSupply",
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
        "name": "combinedReserve",
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
            "name": "num",
            "type": "uint256"
          }
        ],
        "name": "saleCost",
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
            "name": "num",
            "type": "uint256"
          }
        ],
        "name": "sell",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [
          {
            "name": "num",
            "type": "uint256"
          }
        ],
        "name": "purchaseCost",
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
        "name": "auctionStarted",
        "outputs": [],
        "payable": false,
        "type": "function"
      },
      {
        "constant": true,
        "inputs": [],
        "name": "owner_fr",
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
        "name": "base_price",
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
            "name": "_base_price",
            "type": "uint256"
          },
          {
            "name": "_price_factor",
            "type": "uint256"
          },
          {
            "name": "_owner_fr",
            "type": "uint256"
          },
          {
            "name": "_owner_fr_dec",
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
            "name": "_mint",
            "type": "address"
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
            "name": "_auction",
            "type": "address"
          },
          {
            "indexed": true,
            "name": "_token",
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
            "name": "_base_price",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_price_factor",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_owner_fr",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_owner_fr_dec",
            "type": "uint256"
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
        "name": "StartedMinting",
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
            "indexed": false,
            "name": "_funds",
            "type": "uint256"
          }
        ],
        "name": "ReceivedAuctionFunds",
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
            "indexed": true,
            "name": "_num",
            "type": "uint256"
          }
        ],
        "name": "IssuedFromAuction",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_owner",
            "type": "address"
          },
          {
            "indexed": false,
            "name": "_owner_num",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_recipient",
            "type": "address"
          },
          {
            "indexed": false,
            "name": "_recipient_num",
            "type": "uint256"
          }
        ],
        "name": "Issued",
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
            "indexed": true,
            "name": "_value",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_num",
            "type": "uint256"
          }
        ],
        "name": "Bought",
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
            "indexed": true,
            "name": "_num",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_purchase_cost",
            "type": "uint256"
          }
        ],
        "name": "Sold",
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
            "indexed": true,
            "name": "_num",
            "type": "uint256"
          }
        ],
        "name": "Burnt",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_num",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_cost",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_supply",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_timestamp",
            "type": "uint256"
          }
        ],
        "name": "SaleCost",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": true,
            "name": "_num",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_cost",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_supply",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_timestamp",
            "type": "uint256"
          }
        ],
        "name": "PurchaseCost",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": false,
            "name": "_valuation",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_timestamp",
            "type": "uint256"
          }
        ],
        "name": "Valuation",
        "type": "event"
      },
      {
        "anonymous": false,
        "inputs": [
          {
            "indexed": false,
            "name": "_market_cap",
            "type": "uint256"
          },
          {
            "indexed": false,
            "name": "_supply",
            "type": "uint256"
          },
          {
            "indexed": true,
            "name": "_timestamp",
            "type": "uint256"
          }
        ],
        "name": "MarketCap",
        "type": "event"
      }
    ]
}
