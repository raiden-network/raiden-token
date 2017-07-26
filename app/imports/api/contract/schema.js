import SimpleSchema from 'simpl-schema';

export default ContractsSchema = new SimpleSchema({
  name: {
    type: String,
    max: 200,
    optional: true
  },
  address: {
    type: String
  },
  abi: {
    type: String,
    optional: true
  },
  data: {
    type: String,
    optional: true
  },
  gas: {
    type: String,
    optional: true
  },
  networkId: {
    type: String,
    optional: true
  },
  transactionHash: {
    type: String,
    optional: true
  },
  linkedContracts: {
    type: Array,
    optional: true
  },
  'linkedContracts.$': {
    type: String 
  },
  createdAt: {
    type: Date,
    optional: true,
    autoValue: function () {
      if (this.isInsert) {
        return new Date();
      }
    }
  },
  updatedAt: {
    type: Date,
    optional: true,
    autoValue: function () {
      if (this.isUpdate) {
        return new Date();
      }
    }
  },
});
