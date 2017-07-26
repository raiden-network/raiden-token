import React from 'react';
import { Route } from 'react-router-dom';

const RouteWithSubRoutes = (route) => (
  React.createElement(Route, {
    path: route.path, 
    render: props => (
      React.createElement(route.component, { 
        ...route,
        ...props
      })
    )
  })
);

export default RouteWithSubRoutes;