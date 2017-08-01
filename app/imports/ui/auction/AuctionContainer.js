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

  const contractsHandle = Meteor.subscribe('auctions', networkId, 15);
  const tokenHandle = Meteor.subscribe('contract', tokenAddress);

  let contracts = Contracts.find({ linkedContracts: {$exists: 1} }, {sort: {createdAt: -1}}).fetch();
  let auction = contracts.filter(c => c.address == auctionAddress)[0];
  let token = Contracts.findOne({ address: tokenAddress});

  if(auction) {
    auction.abi = JSON.parse(auction.abi);
  }
  if(token) {
    token.abi = JSON.parse(token.abi);
  }

  return {
    web3,
    networkId,
    connected,
    account,
    contracts,
    auction,
    token
  };
}, AuctionPage);

export default AuctionContainer;