import React from 'react';
import { Meteor } from 'meteor/meteor';
import { render } from 'react-dom';

import AppContainer from '../imports/ui/AppContainer.js';

Meteor.startup(() => {
  render(<AppContainer />, document.getElementById('app'));
});
