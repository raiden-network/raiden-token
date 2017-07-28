import React, { Component } from 'react';
import $ from 'jquery';
import { Input, Select, Button } from './components.js';

export default class AddContract extends Component {
  constructor(props) {
    super(props);

    this.addContract = this.addContract.bind(this);
    this.onChange = this.onChange.bind(this);
    this.state = { submitted: 0 };
  }

  onChange(key, value) {
    let obj = {};
    obj[key] = value;
    this.setState(obj);
  }

  addContract(ev) {
    let self = this;
    const { web3, networkId } = this.props;
    let { submitted, address, transactionHash, linkedContracts, name, abi } = this.state;
    this.setState({ submitted : 1 });

    if(!address || !transactionHash || !networkId || !abi) {
      return;
    }

    if(linkedContracts) {
      linkedContracts = linkedContracts.split(',').map(c => c.trim());
    }

    try {
      let json = JSON.parse(abi);
    }
    catch(error) {
      throw "Provided ABI is an incorrect JSON object";
    }

    // Insert contract details in our database
    let obj = { name, address, transactionHash, abi, networkId };
    if(linkedContracts) {
      obj.linkedContracts = linkedContracts;
    }
    console.log(JSON.stringify(obj));
    Meteor.call('contracts.insert', obj);
    this.setState({ 
      submitted : 0, 
      address: '', 
      transactionHash: '', 
      linkedContracts: '', 
      name: '', 
      abi: ''
    });
  }

  render() {
    const { submitted, address, transactionHash, linkedContracts, name, abi } = this.state;

    return React.createElement('div', {
        className: 'col col-1-2 tablet-col-1-1'
      },
      React.createElement(Input, {
        placeholder: 'Name',
        value: name,
        className: (submitted && !name) ? 'dapp-error': '',
        onChange: (value) => this.onChange('name', value)
      }),
      React.createElement(Input, {
        placeholder: 'Address',
        value: address,
        className: (submitted && !address) ? 'dapp-error': '',
        onChange: (value) => this.onChange('address', value)
      }),
      React.createElement(Input, {
        placeholder: 'Transaction Hash',
        value: transactionHash,
        className: (submitted && !transactionHash) ? 'dapp-error': '',
        onChange: (value) => this.onChange('transactionHash', value)
      }),
      React.createElement(Input, {
        placeholder: 'ABI',
        value: abi,
        className: (submitted && !abi) ? 'dapp-error': '',
        onChange: (value) => this.onChange('abi', value)
      }),
      React.createElement(Input, {
        label: 'Linked Contracts',
        value: linkedContracts,
        placeholder: 'address1,address2',
        onChange: (value) => this.onChange('linkedContracts', value)
      }),
      React.createElement(Button, {
        className: 'icon-plus large btn-submit',
        onClick: this.addContract
      })
    );
  }
}
