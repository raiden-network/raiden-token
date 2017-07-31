import React, { Component } from 'react';
import PriceChart from './PriceChart';
import ValueChart from './ValueChart';

// TODO: separate into components

export default class Auction extends Component {
  constructor(props) {
    super(props);
    this.state = this.getInitialState();

    this.priceUpdateInterval = 1000 * 5; // 5 sec
    this.graphDataUpdateInterval = 1000 * 5;
  }

  getInitialState() {
    return {
      priceData: [],
      valueData: [],
      finalTKNPrice: 0,
      currentTKNPrice: 0,
      auctionedTKN: 0,
      estimatedTKNBough: 0,
      auctionReserve: 0
    }
  }

  componentWillMount() {
    this.setValues(this.props);
  }

  componentWillUnmount() {
    clearInterval(this.priceInterval);
    clearInterval(this.priceGraphInterval);
    clearInterval(this.valueGraphInterval);
    this.bidFilter.stopWatching();
    this.bidFilter = null;
  }

  componentWillReceiveProps(newProps) {
    this.state = this.setState(this.getInitialState());
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
      this.startBidLogging();
    }
  }

  setFinalPrice(props) {
    const { auctionInstance } = props;

    auctionInstance.final_price((err, res) => {
      if(err) {
        console.log('setFinalPrice', err);
      }
      if(res) {
        this.setState({ finalTKNPrice: 
          {
            wei: res.toNumber().toLocaleString(),
            eth:  web3.fromWei(res, 'ether').toNumber()
          }
        });
      }
    });
  }

  // Price function used in the Solidity contract
  // Returns Wei per TKN
  auctionPrice(timestamp) {
    timestamp = timestamp || new Date().getTime();
    const { decimals, priceFactor, priceConst, startTimestamp } = this.props;
    let multiplier = Math.pow(10, decimals);

    // Solidity timestamp is in seconds, not miliseconds
    let elapsed = (timestamp - startTimestamp) / 1000;
    let price = multiplier * priceFactor / (elapsed + priceConst) + 1;
    return price;
  }

  // WEI
  getMarketCap(totalSupplyTKN) {
    return totalSupplyTKN * this.auctionPrice();
  }

  // WEI
  getValuation(totalSupplyTKN, auctionedTKN) {
    // Assuming no pre auction reserve
    return this.getMarketCap(totalSupplyTKN) - auctionedTKN * this.auctionPrice();
  }

  getCurrentValuations() {
    let { decimals, totalSupplyTKN, ended } = this.props;
    let { estimatedTKNBough, auctionedTKN } = this.state;
    let preallocations, supply, atok;

    preallocations = totalSupplyTKN - auctionedTKN, 
    supply = ended ? totalSupplyTKN : (preallocations + estimatedTKNBough);

    atok = ended ? auctionedTKN : estimatedTKNBough;

    console.log('totalSupplyTKN, auctionedTKN, preallocations', totalSupplyTKN, auctionedTKN, preallocations)
    console.log('supply, atok', supply, atok)

    // Return Market Cap and Valuation in ETH
    return {
      marketCap: this.getMarketCap(supply) / Math.pow(10, 18),
      valuation: this.getValuation(supply, atok) / Math.pow(10, 18)
    }
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

  updatePriceGraph() {
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

  updateValueGraph() {
    let valueData = this.state.valueData;
    let now = new Date();
    let obj = Object.assign({ 
      date: now, 
      timestamp: now.getTime()
    }, this.getCurrentValuations());
    valueData.push(obj);
    console.log('updateValueGraph', JSON.stringify(obj))
    this.setState({ valueData });
  }

  startPriceInterval() {
    let currentTKNPrice = this.auctionPrice(new Date().getTime());
    this.setState({ currentTKNPrice });

    this.priceInterval = setInterval(() => {
      let currentTKNPrice = this.auctionPrice(new Date().getTime())
      this.setState({ currentTKNPrice });
    }, this.priceUpdateInterval);

    this.priceGraphInterval = setInterval(() => {
      this.updatePriceGraph();
    }, this.graphDataUpdateInterval);

    this.valueGraphInterval = setInterval(() => {
      this.updateValueGraph();
    }, this.graphDataUpdateInterval);
  }

  setTotalTokensAuctioned(props) {
    const { web3, auctionInstance, decimals } = props;

    auctionInstance.tokens_auctioned((err, res) => {
      if(err) {
        console.log('setTotalTokensAuctioned', err);
      }
      if(res) {
        this.setState({ auctionedTKN: res.toNumber() / Math.pow(10, decimals) });
      }
    });
  }

  // TODO delete this after testing
  setAuctionReserve(props) {
    const { web3, auction, auctionInstance, ended } = props;

    // Auction balance in WEI
    web3.eth.getBalance(auction.address, (err, res) => {
      if(err) {
        console.log('setAuctionReserve', err);
      }
      if(res) {
        let auctionReserve, estimatedTKNBough;
        
        auctionReserve = res.toNumber();
        estimatedTKNBough = auctionReserve / this.auctionPrice();
        //this.setState({ auctionReserve, estimatedTKNBough });
        console.log('auctionReserve, estimatedTKNBough', auctionReserve, estimatedTKNBough);
      }
    });
  }

  startBidLogging() {
    const { web3, auctionInstance, getEventFilter } = this.props;

    let handleEv = (err, res) => {
      if(err) {
        console.log('BidSubmission event', err);
        return;
      }

      if(!res.args) {
        return;
      }
      // sender, amount, returned_amount, missing_reserve
      // WEI
      console.log('BidSubmission', res.args);
      let { amount, returned_amount } = res.args;
      let estimatedTKNBough,
        auctionReserve = this.state.auctionReserve;
      
      auctionReserve += amount.toNumber() - (returned_amount ? returned_amount.toNumber() : 0);
      estimatedTKNBough = auctionReserve / this.auctionPrice();

      this.setState({ auctionReserve, estimatedTKNBough });

      console.log('(ev)auctionReserve, estimatedTKNBough', auctionReserve, estimatedTKNBough);

    }

    this.bidFilter = getEventFilter('BidSubmission').get(handleEv);
    this.bidFilter.watch(handleEv);
  }

  render() {
    const { 
      web3,
      networkId,
      account,
      contracts,
      auction,
      decimals,
      ended,
      totalSupplyTKN,
      auctionSupply
    } = this.props;

    const { 
      finalTKNPrice,
      currentTKNPrice: auctionPrice,
      auctionedTKN,
      estimatedTKNBough,
      auctionReserve: auctionReserveWei,
      priceData,
      valueData,
    } = this.state;
    
    let currentTKNPrice,
      auctionReserve,
      marketCap, 
      valuation,
      supply,
      preallocations = totalSupplyTKN - auctionedTKN;

    currentTKNPrice = {
      wei: auctionPrice.toLocaleString(),
      eth: web3.fromWei(auctionPrice, 'ether')
    }

    auctionReserve = {
      wei: auctionReserveWei.toLocaleString(),
      eth: web3.fromWei(auctionReserveWei, 'ether')
    }

    supply = ended ? totalSupplyTKN : (preallocations + estimatedTKNBough);
    // Get Market Cap and Valuation in ETH
    marketCap = this.getMarketCap(supply) / Math.pow(10,18);
    valuation = this.getValuation(supply, ended ? auctionedTKN : estimatedTKNBough) / Math.pow(10,18);

    //console.log('totalSupplyTKN, preallocations, auctionedTKN', totalToks, preallocations, tokAuctioned)
    //console.log('supply, marketCap, valuation', supply, marketCap, valuation);

    console.log('valueData', JSON.stringify(valueData))

    return React.createElement('div', { className: 'dapp-flex-content' },
      React.createElement('div', { className: 'col col-1-1 tablet-col-1-1' },
        ended ? 
          React.createElement('div', {},
            'Final TKN Price: ',
            finalTKNPrice ? finalTKNPrice.wei : 0,
            ' WEI (',
            finalTKNPrice ? finalTKNPrice.eth : 0,
            ' ETH)'
          ) :
          React.createElement('div', {}, 
            'Current TKN Price: ',
            currentTKNPrice ? currentTKNPrice.wei : 0,
            ' WEI (',
            currentTKNPrice ? currentTKNPrice.eth : 0,
            ' ETH)'
          ),
        /*React.createElement('div', {}, 
          'Auction ends when all tokens are bought.'
        ),*/
        React.createElement('div', {}, 
          'Total TKN Auctioned: ',
          auctionedTKN.toLocaleString() || ''
        ),
        !ended ? 
          React.createElement('div', {}, 
            'Estimated TKN Bought: ',
            estimatedTKNBough.toLocaleString() || 0
          ) : null,
        React.createElement('div', {}, 
          'Total raised: ',
          auctionReserve.eth || '0',
          ' ETH'
        ),
        React.createElement('div', {}, 
          'Market Cap: ',
          marketCap || 0,
          ' ETH', ' (preallocs + estimated TKNs bought)'
        ),
        React.createElement('div', {}, 
          'Valuation: ',
          valuation || 0,
          ' ETH'
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
        valueData.length > 1 ? React.createElement('div', {}, 
          React.createElement(ValueChart, { 
            data: valueData,
            width: 650,
            height: 400,
            ratio: 1
          })
        ) : null
      )
    )
  }
}
