import React, { Component } from 'react';
import PropTypes from 'prop-types';

import ContractList from './ContractList';
import ContractUI from './ContractUI.js';
import LoginWarning from './LoginWarning';
import AddContract from './AddContract';


export default class AdminPage extends Component {
  constructor(props) {
    super(props);
    this.state = { values: {} };
    this.command = this.command.bind(this);
  }

  componentWillMount() {
    this.setContractInstance();
  }

  componentWillReceiveProps(newProps) {
    this.setContractInstance(newProps);
  }

  setContractInstance(newProps) {
    let { web3, account, contract } = newProps || this.props;

    if(contract && contract.address) {
      this.contractInstance = web3.eth.contract(contract.abi).at(contract.address);
      this.getOwner();
    }
  }

  getOwner() {
    let self = this;
    let value = this.applyCommand(this.contractInstance, 'owner', [], 0, (value) => {
      console.log('owner', value);
      self.setState({ owner: value });
    });
  }

  getCommands(abi, key, values) {
    if(!(values instanceof Array)) {
      values = [values];
    }
    let commands = [];
    return abi.filter(c => {
      let ok = values.indexOf(c[key]) > -1 && commands.indexOf(c.name) == -1;
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
          callback(res.c ? res.toNumber() : res);
        }
      }
    );
    console.log(command.name, 'input', inputs[0])

    contractInstance[command.name].apply(null, inputs);
  }

  command(command, inputs, payable) {
    console.log('inputs', inputs, this.contractInstance);
    let self = this;
    let value = this.applyCommand(this.contractInstance, command, inputs, payable, (value) => {
      console.log(command.name, value);
      let values = self.state.values;
      values[command.name] = value;
      self.setState({ values });
      //console.log('command', command);
    });
  }

  render() {
    const { web3, networkId, account, contract, contracts } = this.props;
    const { owner, values=[] } = this.state;
    
    let contractUI;
    if(contract) {
      let commands = this.getCommands(contract.abi, "type", 'function');

      contractUI = [
        React.createElement('h1', { key: 1 }, contract.name),
        React.createElement(ContractUI, {
          key: 2,
          web3,
          commands,
          values,
          onClick: this.command
        })
      ];
    }

    return React.createElement('div', { className: 'dapp-flex-content' },
      React.createElement(ContractList, { web3, contracts }),
      React.createElement('div', { className: 'col col-1-1 tablet-col-1-1' },
        contract ? contractUI : React.createElement(AddContract, { web3, networkId }),
      )
    )
  }
}
