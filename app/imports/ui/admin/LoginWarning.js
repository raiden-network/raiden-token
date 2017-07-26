import React, { Component } from 'react';

export default class LoginWarning extends Component {
  render() {
    let { account } = this.props;

    return account ? null : React.createElement('div', {},
      React.createElement('span', {}, 'Log in with MetaMask')
    )
  }
}
