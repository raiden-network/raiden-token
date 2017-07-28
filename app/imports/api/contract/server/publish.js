import { Meteor } from 'meteor/meteor';
import { check, Match } from 'meteor/check';
import Contracts from '../collection.js';

Meteor.publish('contracts', function(networkId, limit) {
  check(networkId, String);
  check(limit, Match.Optional(Number));

  let query = {}, options = {sort: {createdAt: -1}};
  if(networkId) {
    query.networkId = networkId;
  }
  if(limit) {
    options.limit = limit;
  }

  return Contracts.find(query, options);
});

Meteor.publish('contract', function(address) {
  check(address, String);

  return Contracts.find({ address });
});

Meteor.publish('auctions', function(networkId, limit) {
  check(networkId, String);
  check(limit, Match.Optional(Number));

  let query = { linkedContracts: {$exists: 1} }, 
    options = {sort: {createdAt: -1}};
  if(networkId) {
    query.networkId = networkId;
  }
  if(limit) {
    options.limit = limit;
  }

  return Contracts.find(query, options);
});
