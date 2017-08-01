import React, { Component } from 'react';

function NoWeb3(props) {
  return React.createElement('span', {}, 
    'No Web3.js detected. Consider using ',
    React.createElement('a', { href: 'https://metamask.io/', target: '_blank' }, 'MetaMask')
  );
}

export default NoWeb3;