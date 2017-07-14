import React, { Component } from 'react';
import ContractUI from '/imports/ui/ContractUI.js';
import LoginWarning from '/imports/ui/LoginWarning';
import ContractGraphs from '/imports/ui/ContractGraphs';

import { commandMap } from './uiconfig';

export default class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      mintLogs: [],
      auctionLogs: [],
      supplyLogs: [],
      auctionPriceLogs: []
    };
    this.auctionCommand = this.auctionCommand.bind(this);
    this.mintCommand = this.mintCommand.bind(this);
    this.ctokenCommand = this.ctokenCommand.bind(this);
  }

  componentWillMount() {
    this.setCommands();
    this.getAccount();
    this.getOwner();
    //this.watchLogs();
    this.watchLogs('auction', 'AuctionPrice', 'auctionPriceLogs');
  }

  componentDidMount() {
    // Sometimes it does not get set
    this.getAccount();
  }

  // TODO: reliable way to get accounts
  // Make this reactive - if account changes, the app should know
  getAccount() {
    let { web3 } = this.props;
    if(web3.eth.accounts[0]) {
      this.setState({ account: web3.eth.accounts[0] });
    }
    web3.eth.getAccounts(accounts => {
      //console.log('getAccount', accounts)
      let account = accounts ? accounts[0] : false;
      if(account)
        this.setState({ account });
    });
  }

  getOwner() {
    let self = this;
    let value = this.applyCommand(this.auction, 'owner', [], 0, (value) => {
      console.log('owner', value);
      self.setState({ owner: value });
    });
  }

  setCommands() {
    let { web3, contracts, Auction, Mint, CToken } = this.props;

    let auctionUserCommands = this.getCommands(Auction.abi, 'name', commandMap.auction.user);
    let auctionAccountCommands = this.getCommands(Auction.abi, 'name', commandMap.auction.userPersonal);
    let auctionOwnerCommands = this.getCommands(Auction.abi, 'name', commandMap.auction.owner);
    let auctionEvents = this.getCommands(Auction.abi, 'type', 'event');
    this.auction = this.props.web3.eth.contract(Auction.abi).at(Auction.address);

    let mintUserCommands = this.getCommands(Mint.abi, 'name', commandMap.mint.user);
    let mintAccountCommands = this.getCommands(Mint.abi, 'name', commandMap.mint.userPersonal);
    let mintOwnerCommands = this.getCommands(Mint.abi, 'name', commandMap.mint.owner);
    let mintEvents = this.getCommands(Mint.abi, 'type', 'event');
    this.mint = this.props.web3.eth.contract(Mint.abi).at(Mint.address);

    let ctokenUserCommands = this.getCommands(CToken.abi, 'name', commandMap.ctoken.user);
    let ctokenAccountCommands = this.getCommands(CToken.abi, 'name', commandMap.ctoken.userPersonal);
    let ctokenOwnerCommands = this.getCommands(CToken.abi, 'name', commandMap.ctoken.owner);
    let ctokenEvents = this.getCommands(CToken.abi, 'type', 'event');
    this.ctoken = this.props.web3.eth.contract(CToken.abi).at(CToken.address);

    this.setState({
      auctionUserCommands,
      auctionAccountCommands,
      auctionOwnerCommands,
      auctionValues: {},
      auctionEvents,
      mintUserCommands,
      mintAccountCommands,
      mintOwnerCommands,
      mintValues: {},
      mintEvents,
      ctokenUserCommands,
      ctokenAccountCommands,
      ctokenOwnerCommands,
      ctokenValues: {},
      ctokenEvents
    });
  }

  getCommands(abi, key, values) {
    /*if(!(values instanceof Array)) {
      values = [values];
    }*/
    let keys = Object.keys(values);
    let commands = [];
    return abi.filter(c => {
      let ok = keys.indexOf(c[key]) > -1 && commands.indexOf(c.name) == -1;
      if(ok) {
        commands.push(c.name);
        return true;
      }
      return false;
    }).map(c => {
      c.label = values[c.name];
      return c;
    });
  }

  applyCommand(contractInstance, command, inputs=[], payable, callback) {
    let self = this;
    let { account } = this.state;
    let { web3 } = this.props;
    console.log(contractInstance)
    inputs = inputs.concat([
      {
        from: account,
        //to: contractInstance.address,
        value: payable ? parseFloat(payable) : 0,
      },
      function(err, res) {
        if(err) {
          console.log(command.name, err);
        }
        else {
          let value = res.c ? res.c[0] : res;
          callback(value);
        }
      }
    ]);
    console.log(command, 'input', inputs[0])

    contractInstance[command].estimateGas((err, gas) => {
      if(err) {
        console.log('estimateGas', err);
        gas = 4000000;
      }
      console.log('estimateGas', gas);
      inputs[0].gas = gas;
      // Apply command
      contractInstance[command].apply(null, inputs);
    });
  }

  auctionCommand(command, inputs, payable) {
    console.log('inputs', inputs);
    let self = this;
    let value = this.applyCommand(this.auction, command.name, inputs, payable, (value) => {
      console.log(command.name, value);
      let auctionValues = self.state.auctionValues;
      auctionValues[command.name] = value;
      self.setState({ auctionValues })
    });
  }

  mintCommand(command, inputs, payable) {
    console.log('inputs', inputs);
    let self = this;
    let value = this.applyCommand(this.mint, command.name, inputs, payable, (value) => {
      console.log(command.name, value);
      let mintValues = self.state.mintValues;
      mintValues[command.name] = value;
      self.setState({ mintValues })
    });
  }

  ctokenCommand(command, inputs, payable) {
    console.log('inputs', inputs);
    let self = this;
    let value = this.applyCommand(this.ctoken, command.name, inputs, payable, (value) => {
      console.log(command.name, value);
      let ctokenValues = self.state.ctokenValues;
      ctokenValues[command.name] = value;
      self.setState({ ctokenValues })
    });
  }

  watchLogs(contract, event, stateVar) {
    let { web3 } = this.props;
    let self = this;
    console.log('watchLogs')
    // Watching from block 0 is time consuming, so get the block when the contract was created
    let deploymentBlock = web3.eth.getTransaction(Auction.transactionHash, function(err, block) {
      if(err) return;
      console.log('deploymentBlock', block)
      // Watch all events on this contract
      self[contract + 'Filter'] = self[contract][event || 'allEvents']({fromBlock: block.blockNumber, toBlock: 'latest'});
      self[contract + 'Filter'].watch(function(error, log) {
        if(error) {
          console.log(contract + 'Filter', error);
          return;
        }
        console.log(contract + 'Filter', log);
        let logs = self.state[stateVar];
        logs.push(log.args);
        let state = {};
        state[stateVar] = logs;
        self.setState(state);
      });
    });
  }

  render() {
    let { web3 } = this.props;
    let {
      owner,
      account,
      auctionUserCommands,
      auctionAccountCommands,
      auctionOwnerCommands,
      auctionValues,
      auctionEvents,
      mintUserCommands,
      mintAccountCommands,
      mintOwnerCommands,
      mintValues,
      mintEvents,
      ctokenUserCommands,
      ctokenAccountCommands,
      ctokenOwnerCommands,
      ctokenValues,
      ctokenEvents,
      auctionPriceLogs
    } = this.state;
    //let { contract } = this.state;

    return React.createElement('div', {className: 'dapp-flex-content'},
      React.createElement('div', { className: 'col col-1-4 tablet-col-1-3' },
        React.createElement('h1', {}, 'Auction'),
        React.createElement(ContractUI, {
          web3,
          commands: auctionUserCommands,
          values: auctionValues,
          onClick: this.auctionCommand
        }),
        React.createElement('h1', {}, 'Mint'),
        React.createElement(ContractUI, {
          web3,
          commands: mintUserCommands,
          values: mintValues,
          onClick: this.mintCommand
        }),
      ),
      React.createElement(ContractGraphs, {
        web3,
        data: auctionPriceLogs,
        className: 'col col-1-2 tablet-col-1-2'
      }),
      account ? React.createElement('div', { className: 'col col-1-4 tablet-col-1-3' },
        React.createElement('h1', {}, 'Account'),
        React.createElement(ContractUI, {
          web3,
          commands: auctionAccountCommands,
          values: auctionValues,
          onClick: this.auctionCommand
        }),
        React.createElement(ContractUI, {
          web3,
          commands: mintAccountCommands,
          values: mintValues,
          onClick: this.mintCommand }),
        React.createElement(ContractUI, {
          web3,
          commands: ctokenAccountCommands,
          values: ctokenValues,
          onClick: this.ctokenCommand
        }),

        owner === account ? [
          React.createElement('h1', { key: 1 }, 'Owner'),
          React.createElement(ContractUI, {
            web3,
            key: 2,
            commands: auctionOwnerCommands,
            values: auctionValues,
            onClick: this.auctionCommand
          }),
          React.createElement(ContractUI, {
            web3,
            key: 3,
            commands: mintOwnerCommands,
            values: mintValues,
            onClick: this.mintCommand
          }),
          React.createElement(ContractUI, {
            web3,
            key: 4,
            commands: ctokenOwnerCommands,
            values: ctokenValues,
            onClick: this.ctokenCommand
          }),
        ] : null
      ) : React.createElement(LoginWarning, { account })
    )
  }
}

App.propTypes = {
  web3: React.PropTypes.object,
  contracts: React.PropTypes.array,
  loading: React.PropTypes.bool,
  connected: React.PropTypes.bool,
  networkId: React.PropTypes.string
};
