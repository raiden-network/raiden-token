import React, { Component } from 'react';
import { Switch } from 'react-router-dom';

import RouteWithSubRoutes from './RouteWithSubRoutes';
import NoWeb3 from './NoWeb3';

export default class AppContainer extends Component {
  constructor(props) {
    super(props);

    this.state = {};
    this.state.web3 = getWeb3();
  }

  componentWillMount() {
    let self = this;
    let { web3 } = this.state;
    if(!web3) {
      return;
    }
    
    getNetworkId(web3, networkId => {
      self.setState({ networkId });
    });
  }

  // TODO: reliable way to get accounts
  // Make this reactive - if account changes, the app should know
  getAccount() {
    let { web3 } = this.state;
    if(web3.eth.accounts[0]) {
      this.setState({ account: web3.eth.accounts[0] });
    }
    web3.eth.getAccounts(accounts => {
      //console.log('getAccount', accounts)
      let account = accounts ? accounts[0] : false;
      if(account) {
        this.setState({ account });
      }
    });
  }

  render() {
    let { routes } = this.props;
    let { web3, networkId, account } = this.state;

    if(!web3) {
      return NoWeb3();
    }

    if(!networkId) {
      return React.createElement('span', {}, 'No nework detected');
    }

    return React.createElement(Switch, { },
      routes.map((route, i) => (
        React.createElement(RouteWithSubRoutes, {
          key: i,
          web3,
          networkId,
          account,
          connected: Meteor.status().connected, // should be in a container
          ...route,
        })
      ))
    );
  }
}

function getWeb3() {
  // Checking if Web3 has been injected by the browser (Mist/MetaMask)
  if (typeof web3 !== 'undefined') {
    // Use Mist/MetaMask's provider
    window.web3 = new Web3(web3.currentProvider);
  } else if(typeof Web3 !== 'undefined') {
    console.log('No web3? You should consider trying MetaMask!')
    // fallback - use your fallback strategy (local node / hosted node + in-dapp id mgmt / fail)
    window.web3 = new Web3(new Web3.providers.HttpProvider("http://localhost:8545"));
  }

  if(typeof web3 !== 'undefined') {
    console.log("Connected to Web3 Status: " + web3.isConnected());
    return web3;
  }
}

function getNetworkId(web3, callb) {
  web3.version.getNetwork((err, netId) => {
    switch (netId) {
      case "1":
        console.log('This is mainnet');
        break
      case "2":
        console.log('This is the deprecated Morden test network.');
        break
      case "3":
        console.log('This is the ropsten test network.');
        break
      default:
        console.log('This is an unknown network.');
    }
    callb(netId);
  });
}
