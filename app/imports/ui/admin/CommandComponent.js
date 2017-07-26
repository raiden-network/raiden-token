import React, { Component } from 'react';

export default class CommandComponent extends Component {
  constructor(props) {
    super(props);
    this.state = {};
    this.onClick = this.onClick.bind(this);
    this.onChange = this.onChange.bind(this);
    this.inputs = {};
  }

  onClick() {
    let { command, onClick } = this.props;
    let inputsNo = command.inputs.length,
      iNo = Object.keys(this.inputs).length;
      
    if(inputsNo === iNo || inputsNo == iNo - 1) {
      let orderedInputs = command.inputs.map(i => {
        return this.inputs[i.name];
      });
      onClick.call(null, command, orderedInputs, this.inputs.payable);
    }
  }

  onChange(e, key) {
    this.inputs[key] = e.target.value;
    console.log('inputs', this.inputs);
  }

  render() {
    let { command, value } = this.props;
    //console.log(command.name, command.inputs)

    return React.createElement('div', {},
      React.createElement('button', { 
        onClick: this.onClick, 
        className: 'dapp-block-button btn-cmd' 
      }, command.name),
      command.inputs.map((i) => {
        return React.createElement('input', {
          name: 'input', 
          key: i.name,
          //className: 'dapp-sp', 
          placeholder: i.name,
          onChange: (e) => this.onChange(e, i.name)
        });
      }),
      command.payable ? React.createElement('input', {
          name: 'input', 
          key: 'payable',
          //className: 'dapp-sp', 
          placeholder: 'ETH',
          onChange: (e) => this.onChange(e, 'payable')
      }) : null,
      (value || value === 0) ? React.createElement('span', { className: 'dapp-sp' }, value) : null
    );
  }
}