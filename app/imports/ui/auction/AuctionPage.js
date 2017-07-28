import React, { Component } from 'react';
import ContractList from '../admin/ContractList';
import AuctionNotStarted from './AuctionNotStarted';
import Auction from './Auction';
import Loading from '../Loading';

// TODO: loading

export default class AuctionPage extends Component {
  constructor(props) {
    super(props);

    this.state = { stage: 'deployed' };
    this.setValues(props);

    this.addressBuilder = this.addressBuilder.bind(this);
    this.getEventFilter = this.getEventFilter.bind(this);
  }

  componentWillReceiveProps(newProps) {
    this.setState({ stage: 'deployed' });
    this.setValues(newProps);
  }

  setValues(props) {
    props = props || this.props;

    this.setAuctionInstance(props);
    this.setDeploymentBlockNumber(props);
    this.setTokenDecimals(props);
  }

  addressBuilder(contract) {
    return '/auction/' + contract.address + '?linked=' + contract.linkedContracts.join(',');
  }

  setTokenDecimals(props) {
    let self = this;
    const { web3, token } = props || this.props;
    if(!token || !token.address) {
      return;
    }

    let tokenInstance = web3.eth.contract(token.abi).at(token.address);
    tokenInstance.decimals((err, res) => {
      if(err) {
        console.log('setTokenDecimals event', err);
        return;
      }
      self.setState({ decimals: res.toNumber() });
    });
  }

  setAuctionInstance(props) {
    const { web3, auction } = props || this.props;
    if(!auction || !auction.address) {
      return;
    }

    let auctionInstance = web3.eth.contract(auction.abi).at(auction.address);
    this.setState({ auctionInstance });
  }

  setDeploymentBlockNumber(props) {
    let self = this;
    const { auction } = props || this.props;
    if(!auction) {
      return;
    }

    let deploymentBlock = web3.eth.getTransaction(auction.transactionHash, function(err, block) {
      if(err) {
        console.log('deploymentBlock', err);
        return;
      }
      if(block && block.blockNumber) {
        self.setState({ blockNumber: block.blockNumber });
        self.setEventFilters();
      }
    });
  }

  setEventFilters() {
    let self = this;
    
    this.getEventFilter('AuctionStarted').get((err, logs) => {
      if(err) {
        console.log('AuctionStarted event', err);
        return;
      }
      if(logs && logs[0]) {
        self.setState({ stage: 'started'});
      }
    });

    this.getEventFilter('AuctionEnded').get((err, logs) => {
      if(err) {
        console.log('AuctionEnded event', err);
        return;
      }
      if(logs && logs[0]) {
        self.setState({ stage: 'ended'});
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
    const { auctionInstance, stage, decimals } = this.state;
    const { getEventFilter } = this;
    let ended = stage == 'ended' ? 1 : 0;

    return React.createElement('div', { className: 'dapp-flex-content' },
      React.createElement(ContractList, { web3, contracts, addressBuilder: this.addressBuilder }),
      React.createElement('div', { className: 'col col-1-1 tablet-col-1-1' },
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
            auction,
            auctionInstance,
            getEventFilter,
            ended,
          })
      )
    )
  }
}
