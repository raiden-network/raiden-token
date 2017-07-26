import React, { Component } from 'react';
import CommandComponent from './CommandComponent'

export default class ContractUI extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  render() {
    let { contract, web3, commands, values, onClick } = this.props;
    console.log(this.props)
    return React.createElement('div', {},
      React.createElement('div', {},
        commands.map((f, i) => {
          return React.createElement(CommandComponent, {
            web3,
            command: f,
            value: values[f.name],
            key: i,
            onClick
          });
        })
      )
    );
  }
}
