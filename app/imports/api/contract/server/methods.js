import { Meteor } from 'meteor/meteor';
import { ValidatedMethod } from 'meteor/mdg:validated-method';
import Contracts from '../collection.js';
import ContractsSchema from '../schema';

export const contractsInsert = new ValidatedMethod({
  name: 'contracts.insert',
  validate: ContractsSchema.validator(),
  run(obj) {
    return Contracts.insert(obj);
  }
});
