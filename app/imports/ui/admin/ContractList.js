import React, { Component } from 'react';
import { Link } from 'react-router-dom';

export default class ContractList extends Component {
  render() {
    const { contracts=[], onClick } = this.props;

    return React.createElement('div', {className: 'dapp-aside'},
      contracts.map(c => {
        return React.createElement(ContractComponent, { key: c._id, contract: c, onClick });
      })
    );
  }
}

class ContractComponent extends Component {
  constructor(props) {
    super(props);
  }

  render() {
    const { contract } = this.props;

    return React.createElement(Link, {
      className: 'dapp-small',
      //to: '/auction/' + contract.address + '?linked=' + contract.linkedContracts.join(',')
      to: '/admin/' + contract.address
    },
      React.createElement('h3', {}, contract.name)
    );
  }
}
