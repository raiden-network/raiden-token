import { ReactiveVar } from 'meteor/reactive-var';
import { createContainer } from 'meteor/react-meteor-data';
import AuctionPage from './AuctionPage';
import Contracts from '/imports/api/contract/collection';

const AuctionContainer = createContainer((params) => {
  const { 
    web3, 
    networkId, 
    account,
    connected,
    match, 
    location
  } = params;

  const auctionAddress = match.params.address;
  const tokenAddress = location.search.substring(location.search.indexOf('=') + 1);

  const auctionHandle = Meteor.subscribe('contract', auctionAddress);
  const tokenHandle = Meteor.subscribe('contract', tokenAddress);

  let auction = Contracts.findOne({ address: auctionAddress});
  let token = Contracts.findOne({ address: tokenAddress});

  return {
    web3,
    networkId,
    connected,
    account,
    auction,
    token
  };
}, AuctionPage);

export default AuctionContainer;