import React from 'react';
import { render } from 'react-dom';

import {
  BrowserRouter as Router,
  Route,
  Link
} from 'react-router-dom';

import RouteWithSubRoutes from './RouteWithSubRoutes';
import AppContainer from './AppContainer';
import AuctionContainer from '../auction/AuctionContainer';
import AdminContainer from '../admin/AdminContainer';
import HomePage from './HomePage';

const routes = [
  { 
    path: '/',
    component: AppContainer,
    routes: [
      {
        path: '/auction/:address',
        component: AuctionContainer,
      },
      {
        path: '/auction',
        component: AuctionContainer,
      },
      {
        path: '/admin/:address',
        component: AdminContainer,
      },
      {
        path: '/admin',
        component: AdminContainer,
      },
      {
        path: '/',
        component: HomePage,
      }
    ]
  }
]

const Routing = () => (
  React.createElement(Router, {}, 
    React.createElement('div', { className: 'dapp-flex-content' },
      routes.map((route, i) => (
        React.createElement(RouteWithSubRoutes, { key: i, ...route})
      ))
    )
  )
);

export default Routing;