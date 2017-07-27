import React, { Component } from 'react';

export default class AuctionPage extends Component {

  render() {
    const { web3, networkId, account, contract, contracts } = this.props;

    return null;

    return React.createElement('div', { className: 'dapp-flex-content' },
      React.createElement(ContractList, { web3: web3, contracts }),
      React.createElement('div', { className: 'col col-1-1 tablet-col-1-1' },
        //contract ? contractUI : React.createElement(AddContract, { web3, networkId }),
      )
    )
  }
}
