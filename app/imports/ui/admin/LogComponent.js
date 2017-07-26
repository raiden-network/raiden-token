import React, { Component } from 'react';

export default class LogComponent extends Component {
  constructor(props) {
    super(props);
    this.state = { logs: [] };
    this.startLogs = this.startLogs.bind(this);
    this.stopLogs = this.stopLogs.bind(this);
  }

  componentWillMount() {
    this.startLogs();
  }

  componentWillUnmount() {
    this.stopLogs();
  }

  componentWillReceiveProps(nextProps) {
    this.stopLogs();
    this.setState({ logs: [] });
    this.startLogs(nextProps);
  }

  stopLogs() {
    if(this.filter) {
      this.filter.stopWatching();
      this.filter = null;
    }
  }

  startLogs(props) {
    let { web3, contract, instance, events } = props || this.props;
    let self = this;

    // Watching from block 0 is time consuming, so get the block when the contract was created
    let deploymentBlock = web3.eth.getTransaction(contract.transactionHash, function(err, block) {
      if(err) return;

      // Watch all events on this contract
      self.filter = instance.allEvents({fromBlock: block.blockNumber, toBlock: 'latest'});
      self.filter.watch(function(error, log) {
        let logs = self.state.logs;
        logs.push(log);
        self.setState({ logs });
      });
    });
  }

  render() {
    let { logs } = this.state;

    return React.createElement('ul', { className: 'dapp-account-list' },
      logs.map((l, i) => {
        return React.createElement('li', { key: 'li_' + i, className: "dapp-logs" },
          React.createElement('h3', {}, 'Event ' + l.event),
          Object.keys(l.args).map(key => {
            return React.createElement('div', { key }, key + ': ' + l.args[key])
          })
        )
      })
    );
  }
}
