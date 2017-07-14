import React, { Component } from 'react';
import RenderChart from '/imports/ui/RenderChart';

export default class ContractGraphs extends Component {
  constructor(props) {
    super(props);
    this.state = {};
  }

  render() {
    let { data } = this.state;
    console.log('ContractGraphs data', data)
    return React.createElement('div', { className: this.props.className },
      React.createElement(RenderChart, { data })
    );
  }
}
