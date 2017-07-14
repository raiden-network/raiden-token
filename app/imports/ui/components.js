import React, { Component } from 'react';
import $ from 'jquery';

class Input extends Component {
  constructor(props) {
    super(props);
    this.onChange = this.onChange.bind(this);
  }

  onChange(ev) {
    this.props.onChange($(ev.target).val());
  }

  render() {
    let { className, label } = this.props;

    return React.createElement('div', {},
      React.createElement('input',
        {name: 'input', className,  label: 'Title', defaultValue: this.props.defaultValue, onChange: this.onChange}
      ),
      React.createElement('span', {}, label)
    );
  }
}

class Select extends Component {
  constructor(props) {
    super(props);
    this.onChange = this.onChange.bind(this);
  }

  onChange(ev) {
    this.props.onChange($(ev.target).val());
  }

  render() {
    const { label, options, className } = this.props;

    return React.createElement('div', {},
      React.createElement('select',
        {name: 'select', onChange: this.onChange},
        options.map((o, i) => {
          return React.createElement('option', {value:  o.value, key: i}, o.label);
        })
      ),
      React.createElement('span', { className }, label)
    );
  }
}

class Button extends Component {
  constructor(props) {
    super(props);
    this.onClick = this.props.onClick.bind(this);
  }

  render() {
    const { label, onClick, className } = this.props;
    return React.createElement('button',
      {name: 'button', onClick: this.onClick, className}, label
    );
  }
}

export { Input, Select, Button };
