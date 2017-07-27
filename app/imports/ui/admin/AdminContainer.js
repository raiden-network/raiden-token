import { ReactiveVar } from 'meteor/reactive-var';
import { createContainer } from 'meteor/react-meteor-data';
import Contracts from '/imports/api/contract/collection';
import AdminPage from './AdminPage';

const AdminContainer = createContainer(params => {
  const { 
    web3, 
    networkId, 
    account,
    connected,
    match, 
  } = params;

  console.log(params);
  const address = match.params.address;

  let contractsHandle = Meteor.subscribe('contracts', networkId, 15);
  let contracts = Contracts.find({}, {sort: {createdAt: -1}}).fetch();

  let contract = contracts.filter(c => c.address == address)[0];
  if(contract) {
    contract.abi = JSON.parse(contract.abi);
  }

  return {
    web3,
    networkId,
    connected,
    account,
    contract, 
    contracts
  };
}, AdminPage);

export default AdminContainer;