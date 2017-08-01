import React, { Component } from 'react';

export default class AuctionNotStarted extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  componentWillMount() {
    this.setValues(this.props);
  }

  componentWillReceiveProps(newProps) {
    this.setValues(newProps);
  }

  setValues(props) {
    props = props || this.props;
    const { auctionInstance } = props;

    if(!auctionInstance) {
      return;
    }

    this.setTotalTokensAuctioned(props);
    this.setStartingPrice(props);
  }

  setStartingPrice(props) {
    const { auctionInstance } = props;

    auctionInstance.price((err, res) => {
      if(err) {
        console.log('price', err);
      }
      if(res) {
        this.setState({ startingPrice: 
          {
            wei: res.toNumber().toLocaleString(),
            eth:  web3.fromWei(res, 'ether').toNumber()
          }
        });
      }
    });
  }

  setTotalTokensAuctioned(props) {
    const { web3, auctionInstance } = props;

    auctionInstance.tokens_auctioned((err, res) => {
      if(err) {
        console.log('setTotalTokensAuctioned', err);
      }
      if(res) {
        const { decimals } = this.props;
        let tokenNo = res.toNumber();
        let decimalNo = Math.pow(10, decimals);
        tokenNo /= decimalNo;

        this.setState({ tokensAuctioned: tokenNo.toLocaleString() });
      }
    });
  }

  render() {
    const { web3, networkId, account, contracts, auction, token } = this.props;
    const { startingPrice, tokensAuctioned } = this.state;

    return React.createElement('div', { className: 'dapp-flex-content' },
      React.createElement('div', { className: 'col col-1-1 tablet-col-1-1' },
        React.createElement('div', {}, 
          'Auction Starts in  x days: x min: x sec'
        ),
        React.createElement('div', {}, 
          'Starting Price: ',
          startingPrice ? startingPrice.wei : 0,
          ' WEI (',
          startingPrice ? startingPrice.eth : 0,
          ' ETH)'
        ),
        React.createElement('div', {}, 
          'Total Tokens Auctioned: ',
          tokensAuctioned || ''
        ),
        React.createElement('div', {}, 
          'FAQ / process description'
        ),
      )
    )
  }
}
