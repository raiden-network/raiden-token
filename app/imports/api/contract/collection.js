import { Mongo } from 'meteor/mongo';
import 'meteor/aldeed:collection2-core';
import ContractsSchema from './schema';

const Contracts = new Mongo.Collection("contracts");
Contracts.attachSchema(ContractsSchema);

export default Contracts;