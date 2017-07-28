import React, { Component } from 'react';
import { Link } from 'react-router-dom';

export default class ContractList extends Component {
  render() {
    const { contracts=[], onClick, addressBuilder } = this.props;

    return React.createElement('div', {className: 'dapp-aside'},
      contracts.map(c => {
        return React.createElement(ContractComponent, { key: c._id, contract: c, onClick, addressBuilder });
      })
    );
  }
}

class ContractComponent extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    const { contract, addressBuilder } = this.props;

    return React.createElement(Link, {
      className: 'dapp-small',
      to: addressBuilder ? addressBuilder(contract) : '/admin/' + contract.address
    },
      React.createElement('h3', {}, contract.name)
    );
  }
}
