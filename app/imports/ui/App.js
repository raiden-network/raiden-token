import React, { Component } from 'react';
import ContractUI from '/imports/ui/ContractUI.js';
import LoginWarning from '/imports/ui/LoginWarning';
import { PriceChart } from '/imports/ui/PriceChart';

import { commandMap } from './uiconfig';

export default class App extends Component {
  constructor(props) {
    super(props);
    this.state = {
      priceData: [],
      polledPriceData: []
    };
    this.auctionCommand = this.auctionCommand.bind(this);
    this.mintCommand = this.mintCommand.bind(this);
    this.ctokenCommand = this.ctokenCommand.bind(this);
  }

  componentWillMount() {
    this.setCommands();
    this.setInputMaps();
    this.getAccount();
    this.getOwner();
    this.watchLogs();
  }

  componentDidMount() {
    // Sometimes it does not get set
    this.getAccount();
  }

  componentWillUnmount() {
    this.stopPolling();
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
    if(typeof command == 'string') {
      command = { name: command, constant: true };
    }
    console.log(contractInstance)
    console.log('payable', payable)

    if(!command.constant) {
      inputs.push({
        from: account,
        //to: contractInstance.address,
        value: web3.toWei(payable ? parseFloat(payable) : 0, "ether")
      });
    }

    inputs.push(
      function(err, res) {
        if(err) {
          console.log(command.name, err);
        }
        else {
          let value = res.c ? res.c[0] : res;
          callback(value);
        }
      }
    );
    console.log(command.name, 'input', inputs[0])

    /*contractInstance[command.name].estimateGas((err, gas) => {
      if(err) {
        console.log('estimateGas', err);
        gas = 4000000;
      }
      console.log('estimateGas', gas);
      inputs[0].gas = gas;
      console.log(command.name, 'input', JSON.stringify(inputs[0]))
      // Apply command
      contractInstance[command.name].apply(null, inputs);
    });*/
    contractInstance[command.name].apply(null, inputs);
  }

  auctionCommand(command, inputs, payable) {
    console.log('inputs', inputs);
    let self = this;
    let value = this.applyCommand(this.auction, command, inputs, payable, (value) => {
      console.log(command.name, value);
      let auctionValues = self.state.auctionValues;
      auctionValues[command.name] = value;
      self.setState({ auctionValues });
      //console.log('command', command);
      if(command.name === 'price') {
        let priceData = self.state.priceData;
        priceData.push({ price: value, timestamp: new Date().getTime() });
        self.setState({ priceData });
      }
    });
  }

  mintCommand(command, inputs, payable) {
    console.log('inputs', inputs);
    let self = this;
    let value = this.applyCommand(this.mint, command, inputs, payable, (value) => {
      console.log(command.name, value);
      let mintValues = self.state.mintValues;
      mintValues[command.name] = value;
      self.setState({ mintValues })
    });
  }

  ctokenCommand(command, inputs, payable) {
    console.log('inputs', inputs);
    let self = this;
    let value = this.applyCommand(this.ctoken, command, inputs, payable, (value) => {
      console.log(command.name, value);
      let ctokenValues = self.state.ctokenValues;
      ctokenValues[command.name] = value;
      self.setState({ ctokenValues })
    });
  }

  setInputMaps() {
    let { Auction, Mint, CToken } = this.props;
    let events = {},
      commands = {};
    Auction.abi.forEach(c => {
      if(c.type == 'event') {
        events[c.name] = { inputs: c.inputs };
      }
      if(c.type == 'function' && (!commands[c.name] || !c.inputs.length)) {
        commands[c.name] = { inputs: c.inputs, outputs: c.outputs };
      }
    });
    this.events = events;
    this.commands = commands;
  }

  watchLogs() {
    let { web3 } = this.props;
    let self = this;
    //console.log('watchLogs')
    // Watching from block 0 is time consuming, so get the block when the contract was created
    let deploymentBlock = web3.eth.getTransaction(Auction.transactionHash, function(err, block) {
      if(err) return;

      self.auctionFilter = self.auction.allEvents({fromBlock: block.blockNumber, toBlock: 'latest'});
      self.auctionFilter.get((err, log) => {
        if(err) {
          console.log('---Log', err);
        }
        else {
          self.readLog(log, 'auction');
        }
      });
      self.auctionFilter.watch((err, log) => {
        if(err) {
          console.log('----Log', err);
        }
        else {
          self.readLog(log, 'auction');
        }
      });
    });
  }

  readLog(log, type) {
    console.log('--Log', log.event, log);
    let self = this;
    if(log.event == 'AuctionStarted' && type == 'auction') {
      self.startPolling();
    }
    if(log.event == 'AuctionEnded' && type == 'auction') {
      self.stopPolling();
    }
    /*if(['Ordered', 'Bought', 'Sold', 'Burnt'].indexOf(log.event) > -1) {
      let obj = {};

      this.applyCommand(this.auction, 'price', [], 0, (value) => {
        obj.auctionPrice = value;

        self.applyCommand(self.mint, 'ask', [], 0, (value) => {
          obj.mintSale = value;

          self.applyCommand(self.mint, 'purchaseCost', [1], 0, (value) => {
            obj.mintPurchase = value;

            self.applyCommand(self.mint, 'supplyAtReserve', [], 0, (value) => {
              obj.supply = value;

              console.log('price data', obj);
              let priceData = self.state.priceData;
              priceData.push(obj);
              self.setState({ priceData });
            });
          });
        });
      });
    }*/
    
    if(log.event == 'AuctionPrice' && type == 'auction') {
      console.log('--Log', log);
      let priceData = self.state.priceData;
      priceData.push({ auctionPrice: log.args._price.c[0], timestamp: log.args._timestamp.c[0] * 1000 });
      self.setState({ priceData });
    }
    if(log.event == 'SaleCost') {
      console.log('--Log', log);
      let priceData = self.state.priceData;
      priceData.push({ mintSale: log.args._cost.c[0], timestamp: log.args._timestamp.c[0] * 1000 });
      self.setState({ priceData });
    }
    if(log.event == 'PurchaseCost') {
      console.log('--Log', log);
      let priceData = self.state.priceData;
      priceData.push({ mintPurchase: log.args._cost.c[0], timestamp: log.args._timestamp.c[0] * 1000 });
      self.setState({ priceData });
    }
  }

  setChartData() {
    let self = this;
    let obj = {};
    console.log('setChartData', this)
    this.applyCommand(this.auction, 'price', [], 0, (value) => {
      obj.auctionPrice = value;

      self.applyCommand(self.mint, 'ask', [], 0, (value) => {
        obj.mintSale = value;

        self.applyCommand(self.mint, 'purchaseCost', [1], 0, (value) => {
          obj.mintPurchase = value;

          self.applyCommand(self.mint, 'supplyAtReserve', [], 0, (value) => {
            obj.supply = value;
            obj.timestamp = new Date().getTime();

            console.log('**polled price data', obj);
            let polledPriceData = self.state.polledPriceData;
            polledPriceData.push(obj);
            self.setState({ polledPriceData });
          });
        });
      });
    });
  }

  startPolling() {
    console.log('startPolling')
    this.intervalID = window.setInterval(this.setChartData.bind(this), 2000);
  }

  stopPolling() {
    console.log('stopPolling')
    if(this.intervalID)
        clearInterval(this.intervalID);
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
      priceData,
      polledPriceData
    } = this.state;
    //let { contract } = this.state;
    console.log('render priceData', priceData);

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
      //React.createElement(ContractGraphs, {
      React.createElement('div', { className: 'col col-1-2 tablet-col-1-2' },
        /*priceData 
          ? React.createElement(PriceChart, {
            type: 'hybrid',
            width: 650,
            height: 400,
            ratio: 1,
            data: priceData,
            startTimestamp: new Date(2017, 6, 16), 
            endTimestamp: new Date(2017, 6, 18)
          })
          : null,*/

        polledPriceData 
          ? React.createElement(PriceChart, {
            type: 'hybrid',
            width: 650, 
            height: 400,
            ratio: 1,
            data: polledPriceData,
            startTimestamp: new Date(2017, 6, 16), 
            endTimestamp: new Date(2017, 6, 18)
          })
          : null,
      ),
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
