let commandMap = {
  auction: {
    user: {
      price: 'Price',
      stage: 'Stage',
      missingReserveToEndAuction: 'Missing Reserve',
      auctionMarketCap: 'Market Cap',
      auctionValuation: 'Valuation',
      received_value: 'Final Auction Reserve',
      total_issuance: 'Final Auction Issuance',
      issued_value: 'Tokens Claimed',
    },
    userPersonal: {
      order: 'Order',
    },
    owner: {
      changeSettings: 'Change Auction Settings',
      startAuction: 'Start Auction',
      claimTokens: 'Claim Tokens',
    }
  },
  mint: {
    user: {
      valuation: 'valuation',
      marketCap: 'Market Cap',
      combinedReserve: 'Total Reserve',
      purchaseCost: 'Purchase Cost',
    },
    userPersonal: {
      //curveIssuable: 'Curve Issuable',
      ask: 'Ask',
      saleCost: 'Sale Cost',
      burn: 'Burn',
      sell: 'Sell',
      buy: 'Buy',
    },
    owner: {
      changeSettings: 'Change Mint Settings',
    }
  },
  ctoken: {
    user: {
      totalSupply: 'Tokens Issued',
    },
    userPersonal: {
      balanceOf: 'Balance',
      transfer: 'transfer',
    },
    owner: {

    }
  }
}

export { commandMap }