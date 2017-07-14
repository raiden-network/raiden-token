import { ReactiveVar } from 'meteor/reactive-var';
import { createContainer } from 'meteor/react-meteor-data';

import Auction from '/imports/api/build/auction';
import Mint from '/imports/api/build/mint';
import CToken from '/imports/api/build/ctoken';

import App from './App.js';

let called = 0;
export default AppContainer = createContainer(() => {

  const web3 = getWeb3();
  let networkId = new ReactiveVar('');
  if(!called)
    getNetworkId(web3, (id) => {
      called = 1;
      networkId.set(id);
    });

  return {
    web3,
    networkId: networkId.get(),
    connected: Meteor.status().connected,
    Auction, 
    Mint, 
    CToken
  };
}, App);

function getWeb3() {
  // Checking if Web3 has been injected by the browser (Mist/MetaMask)
  if (typeof web3 !== 'undefined') {
    // Use Mist/MetaMask's provider
    window.web3 = new Web3(web3.currentProvider);
  } else {
    console.log('No web3? You should consider trying MetaMask!')
    // fallback - use your fallback strategy (local node / hosted node + in-dapp id mgmt / fail)
    window.web3 = new Web3(new Web3.providers.HttpProvider("http://localhost:8545"));
  }

  console.log("Connected to Web3 Status: " + web3.isConnected());

  return web3;
}

function getNetworkId(web3, callb) {
  web3.version.getNetwork((err, netId) => {
    switch (netId) {
      case "1":
        console.log('This is mainnet');
        break
      case "2":
        console.log('This is the deprecated Morden test network.');
        break
      case "3":
        console.log('This is the ropsten test network.');
        break
      default:
        console.log('This is an unknown network.');
    }
    callb(netId);
  });
}
