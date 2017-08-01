import React, { Component } from 'react';
import { Link } from 'react-router-dom';

export default class HomePage extends Component {

  render() {
    const { location } = this.props;

    return React.createElement('div', {},
      React.createElement('div', {},
        React.createElement(Link, {
          className: 'dapp-small',
          to: '/admin'
        },
          'Admin'
        ),
        ' - register and test already deployed smart contracts.'
      ),
      React.createElement('div', {},
        React.createElement(Link, {
          className: 'dapp-small',
          to: '/auction'
        },
          'Auction View'
        ),
        ' - test registered auction contracts.'
      )
    );
  }
}