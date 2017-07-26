import React from 'react';
import { Meteor } from 'meteor/meteor';
import { render } from 'react-dom';

import Routing from '/imports/ui/app/routes.js';

Meteor.startup(() => {
  render(React.createElement(Routing), document.getElementById('app'));
});