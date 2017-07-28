import React, { Component } from 'react';
import BigNumber from 'bignumber.js';

export default class AuctionStarted extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  componentWillMount() {
    this.setValues(this.props);
  }

  componentWillReceiveProps(newProps) {
    this.setValues(newProps);
  }

  setValues(props) {
    props = props || this.props;
    const { auctionInstance } = props;

    if(!auctionInstance) {
      return;
    }

    this.setTotalTokensAuctioned(props);
    this.setAuctionReserve(props);
    this.setMarketCap(props);
    this.setValuation(props);

    if(props.ended) {
      this.setFinalPrice(props);
    }
    else {
      this.setEstimatedTokensBought(props);
    }
  }

  setFinalPrice(props) {
    let self = this;
    const { auctionInstance } = props;

    auctionInstance.final_price((err, res) => {
      if(err) {
        console.log('setFinalPrice', err);
      }
      if(res) {
        self.setState({ finalPrice: 
          {
            wei: res.toNumber().toLocaleString(),
            eth:  web3.fromWei(res, 'ether').toNumber()
          }
        });
      }
    });
  }

  setCurrentPrice(props) {
    let self = this;
  }

  setTotalTokensAuctioned(props) {
    let self = this;
    const { web3, auctionInstance } = props;

    auctionInstance.tokens_auctioned((err, res) => {
      if(err) {
        console.log('setTotalTokensAuctioned', err);
      }
      if(res) {
        const { decimals } = self.props;
        let tokenNo = res.toNumber();
        let decimalNo = Math.pow(10, decimals);
        tokenNo /= decimalNo;

        self.setState({ tokensAuctioned: tokenNo.toLocaleString() });
      }
    });
  }

  setEstimatedTokensBought(props) {
    let self = this;
  }

  setAuctionReserve(props) {
    let self = this;
    const { web3, auction, auctionInstance } = props;

    web3.eth.getBalance(auction.address, (err, res) => {
      if(err) {
        console.log('setAuctionReserve', err);
      }
      if(res) {
        self.setState({ auctionReserve: web3.fromWei(res, 'ether').toNumber() });
      }
    });
  }

  setMarketCap(props) {
    let self = this;
  }

  setValuation(props) {
    let self = this;
  }

  render() {
    const { web3, networkId, account, contracts, auction, ended } = this.props;
    const { 
      finalPrice,
      currentPrice,
      tokensAuctioned,
      estimatedTokensBough,
      auctionReserve,
      marketCap,
      valuation,
      noOfBidders
    } = this.state;


    return React.createElement('div', { className: 'dapp-flex-content' },
      React.createElement('div', { className: 'col col-1-1 tablet-col-1-1' },
        ended ? 
          React.createElement('div', {},
            'Final Token Price: ',
            finalPrice ? finalPrice.wei : 0,
            ' WEI (',
            finalPrice ? finalPrice.eth : 0,
            ' ETH)'
          ) :
          React.createElement('div', {}, 
            'Current Token Price: ',
            currentPrice ? currentPrice.wei : 0,
            ' WEI (',
            currentPrice ? currentPrice.eth : 0,
            ' ETH)'
          ),
        /*React.createElement('div', {}, 
          'Auction ends when all tokens are bought.'
        ),*/
        React.createElement('div', {}, 
          'Total Tokens Auctioned: ',
          tokensAuctioned || ''
        ),
        !ended ? 
          React.createElement('div', {}, 
            'Estimated Tokens Bought: ',
            estimatedTokensBough || ''
          ) : null,
        React.createElement('div', {}, 
          'Total raised: ',
          auctionReserve || '0',
          ' ETH'
        ),
        React.createElement('div', {}, 
          'Market Cap: ',
          marketCap || ''
        ),
        React.createElement('div', {}, 
          'Valuation: ',
          valuation || ''
        ),
        React.createElement('div', {}, 
          'Price Graph'
        ),
        React.createElement('div', {}, 
          'Market Cap / Valuation Graph'
        )
      )
    )
  }
}
