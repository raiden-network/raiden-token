import React, { Component } from 'react';
import PriceChart from './PriceChart';
import ValueChart from './ValueChart';

export default class Auction extends Component {
  constructor(props) {
    super(props);
    this.state = { priceData: [] };

    this.priceUpdateInterval = 1000 * 5; // 5 sec
    this.graphDataUpdateInterval = 1000 * 5;
  }

  componentWillMount() {
    this.setValues(this.props);
  }

  componentWillUnmount() {
    clearInterval(this.priceInterval);
    clearInterval(this.priceGraphInterval);
  }

  componentWillReceiveProps(newProps) {
    this.state = { priceData: [] };
    this.setValues(newProps);
  }

  setValues(props) {
    props = props || this.props;
    const { auctionInstance, startTimestamp, endTimestamp } = props;

    if(!auctionInstance) {
      return;
    }

    this.setTotalTokensAuctioned(props);
    this.setAuctionReserve(props);
    let data = this.getPriceInInterval(startTimestamp, endTimestamp || new Date().getTime());
    this.setState({ priceData: data });

    if(props.ended) {
      this.setFinalPrice(props);
    }
    else {
      this.startPriceInterval();
    }
  }

  setFinalPrice(props) {
    const { auctionInstance } = props;

    auctionInstance.final_price((err, res) => {
      if(err) {
        console.log('setFinalPrice', err);
      }
      if(res) {
        this.setState({ finalPrice: 
          {
            wei: res.toNumber().toLocaleString(),
            eth:  web3.fromWei(res, 'ether').toNumber()
          }
        });
      }
    });
  }

  // Price function used in the Solidity contract
  auctionPrice(timestamp) {
    timestamp = timestamp || new Date().getTime();
    const { decimals, priceFactor, priceConst, startTimestamp } = this.props;
    let multiplier = Math.pow(10, decimals);

    // Solidity timestamp is in seconds, not miliseconds
    let elapsed = (timestamp - startTimestamp) / 1000;
    let price = multiplier * priceFactor / (elapsed + priceConst) + 1;
    return price;
  }

  getMarketCap() {
    const { totalSupply } = this.props;
    return totalSupply * this.auctionPrice();
  }

  getValuation() {
    const { tokensAuctioned } = this.state;

    // Assuming no pre auction reserve
    return this.getMarketCap() - tokensAuctioned * this.auctionPrice();
  }

  getPriceInInterval(start, end) {
    let data = [],
      interval = Math.min((end - start) / 100, this.graphDataUpdateInterval);

    console.log('getPriceInInterval', start, new Date(start), end, new Date(end))
    console.log('interval', interval, (end - start) / 100, this.graphDataUpdateInterval)
    
    for(let i = start; i < end; i += interval) {
      let priceWei = this.auctionPrice(i);

      data.push({
        date: new Date(i),
        timestamp: i,
        priceWei,
        priceEth: web3.fromWei(priceWei, 'ether') 
      });
    }
    return data;
  }

  startPriceInterval() {
    let currentPrice = this.auctionPrice(new Date().getTime());
    this.setState({ currentPrice });

    let updateGraphPrice = () => {
      let priceData = this.state.priceData;
      let now = new Date(),
        priceWei = this.auctionPrice(now);

      priceData.push({ 
        date: now, 
        timestamp: now.getTime(), 
        priceWei,
        priceEth: web3.fromWei(priceWei, 'ether') 
      });
      this.setState({ priceData });
    }

    this.priceInterval = setInterval(() => {
      let currentPrice = this.auctionPrice(new Date().getTime())
      this.setState({ currentPrice });
    }, this.priceUpdateInterval);

    this.priceGraphInterval = setInterval(function() {
      updateGraphPrice();
    }, this.graphDataUpdateInterval);
  }

  setTotalTokensAuctioned(props) {
    const { web3, auctionInstance } = props;

    auctionInstance.tokens_auctioned((err, res) => {
      if(err) {
        console.log('setTotalTokensAuctioned', err);
      }
      if(res) {
        const { decimals } = this.props;
        let tokenNo = res.toNumber();
        let decimalNo = Math.pow(10, decimals);
        tokenNo /= decimalNo;

        this.setState({ tokensAuctioned: tokenNo.toLocaleString() });
      }
    });
  }

  setAuctionReserve(props) {
    const { web3, auction, auctionInstance, ended } = props;

    web3.eth.getBalance(auction.address, (err, res) => {
      if(err) {
        console.log('setAuctionReserve', err);
      }
      if(res) {
        let auctionReserve = web3.fromWei(res, 'ether').toNumber()
        this.setState({ auctionReserve });
        if(!ended) {
          let estimatedTokensBough = (auctionReserve / this.auctionPrice()).toFixed(20);
          this.setState({ estimatedTokensBough });
        }
      }
    });
  }

  render() {
    const { web3, networkId, account, contracts, auction, ended, startTimestamp, endTimestamp } = this.props;
    const { 
      finalPrice,
      currentPrice: auctionPrice,
      tokensAuctioned,
      estimatedTokensBough,
      auctionReserve,
      marketCap,
      valuation,
      priceData,
    } = this.state;
    
    let currentPrice;
    if(auctionPrice) {
      currentPrice = {
        wei: auctionPrice.toLocaleString(),
        eth: web3.fromWei(auctionPrice, 'ether')
      }
    }

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
          React.createElement(PriceChart, { 
            data: priceData,
            width: 650,
            height: 400,
            ratio: 1,
            priceKey: 'priceWei'
          })
        ),
        React.createElement('div', {}, 
          'Market Cap / Valuation Graph:'
        )
      )
    )
  }
}
