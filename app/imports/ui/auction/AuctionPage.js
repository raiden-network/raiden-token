import React, { Component } from 'react';
import ContractList from '../admin/ContractList';
import AuctionNotStarted from './AuctionNotStarted';
import Auction from './Auction';
import Loading from '../Loading';

// TODO: loading template 
// (setState error because AuctionStarted gets mounted and quickly unmounted if auction started)

export default class AuctionPage extends Component {
  constructor(props) {
    super(props);

    this.state = this.getInitialState();
    this.setValues(props);

    this.addressBuilder = this.addressBuilder.bind(this);
    this.getEventFilter = this.getEventFilter.bind(this);
  }

  getInitialState() {
    return {
      stage: 'deployed',
      totalSupplyTKN: 0,
      decimals: 0
    }
  }

  componentWillReceiveProps(newProps) {
    this.setState(this.getInitialState());
    this.setValues(newProps);
  }

  setValues(props) {
    props = props || this.props;

    this.setAuctionInstance(props);
    this.setDeploymentBlockNumber(props);
    this.setTokenInstance(props);
  }

  addressBuilder(contract) {
    return '/auction/' + contract.address + '?linked=' + contract.linkedContracts.join(',');
  }

  setTokenInstance(props) {
    const { web3, token } = props || this.props;
    if(!token || !token.address) {
      return;
    }

    let tokenInstance = web3.eth.contract(token.abi).at(token.address);
    this.setState({ tokenInstance });
    this.setTokenDecimals(tokenInstance);
    this.setTokenSupply(tokenInstance);
  }

  setTokenDecimals(tokenInstance) {
    tokenInstance.decimals((err, res) => {
      if(err) {
        console.log('setTokenDecimals event', err);
        return;
      }
      this.setState({ decimals: res.toNumber() });
    });
  }

  setTokenSupply(tokenInstance) {
    tokenInstance.totalSupply((err, res) => {
      if(err) {
        console.log('setTKNSupply event', err);
        return;
      }
      let decimals = this.state.decimals,
        totalSupplyTKN = res.toNumber() / Math.pow(10, decimals);
      console.log('set totalSupplyTKN', totalSupplyTKN);
      this.setState({ totalSupplyTKN });
    });
  }

  setAuctionInstance(props) {
    const { web3, auction } = props || this.props;
    if(!auction || !auction.address) {
      return;
    }

    let auctionInstance = web3.eth.contract(auction.abi).at(auction.address);
    this.setState({ auctionInstance });
    this.setPriceFactor(auctionInstance);
    this.setPriceConstant(auctionInstance);
    this.setStartTimestamp(auctionInstance);
  }

  setDeploymentBlockNumber(props) {
    const { auction } = props || this.props;
    if(!auction) {
      return;
    }

    let deploymentBlock = web3.eth.getTransaction(auction.transactionHash, (err, block) => {
      if(err) {
        console.log('deploymentBlock', err);
        return;
      }
      if(block && block.blockNumber) {
        this.setState({ blockNumber: block.blockNumber });
        this.setEventFilters();
      }
    });
  }

  setPriceFactor(auctionInstance) {
    auctionInstance.price_factor((err, res) => {
      if(err) {
        console.log('setPriceFactor', err);
        return;
      }
      if(res) {
        this.setState({ priceFactor: res.toNumber() });
      }
    });
  }

  setPriceConstant(auctionInstance) {
    auctionInstance.price_const((err, res) => {
      if(err) {
        console.log('setPriceConstant', err);
        return;
      }
      if(res) {
        this.setState({ priceConst: res.toNumber() });
      }
    });
  }

  setStartTimestamp(auctionInstance) {
    auctionInstance.start_time((err, res) => {
      if(err) {
        console.log('setStartTimestamp', err);
        return;
      }
      if(res) {
        this.setState({ startTimestamp: res.toNumber() * 1000 });
      }
    });
  }

  setEventFilters() {
    this.getEventFilter('AuctionStarted').get((err, logs) => {
      if(err) {
        console.log('AuctionStarted event', err);
        return;
      }
      if(logs && logs[0] && this.state.stage == 'deployed') {
        this.setState({ stage: 'started'});
      }
    });

    this.getEventFilter('AuctionEnded').get((err, logs) => {
      if(err) {
        console.log('AuctionEnded event', err);
        return;
      }
      if(logs && logs[0]) {
        this.setState({ stage: 'ended'});
      }
    });
  }

  getEventFilter(eventType, eventValues = {}) {
    const { auctionInstance, blockNumber } = this.state;
    let filter;
    if(!auctionInstance || !blockNumber) {
      return;
    }

    if(!eventType) {
      filter = auctionInstance.allEvents({fromBlock: blockNumber, toBlock: 'latest'});
    }
    else {
      filter = auctionInstance[eventType](eventValues, {fromBlock: blockNumber, toBlock: 'latest'});
    }

    return filter;
  }

  render() {
    const { web3, networkId, account, contracts, auction, token } = this.props;
    const { 
      auctionInstance,
      stage,
      decimals,
      totalSupplyTKN,
      priceFactor, 
      priceConst, 
      startTimestamp,
    } = this.state;

    const { getEventFilter } = this;
    let ended = stage == 'ended' ? 1 : 0;

    return React.createElement('div', { className: 'dapp-flex-content' },
      React.createElement(ContractList, { 
        web3,
        contracts,
        addressBuilder: this.addressBuilder
      }),
      !auction ? null : React.createElement('div', { 
          className: 'col col-1-1 tablet-col-1-1' 
        },
        stage == 'deployed' ? 
          React.createElement(AuctionNotStarted, { 
            web3, 
            networkId,
            decimals,
            auction,
            auctionInstance,
            getEventFilter,
          }) :
          React.createElement(Auction, { 
            web3, 
            networkId,
            decimals,
            totalSupplyTKN,
            auction,
            auctionInstance,
            getEventFilter,
            ended,
            priceFactor, 
            priceConst, 
            startTimestamp,
          })
      )
    )
  }
}
