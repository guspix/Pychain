import hashlib as hasher
import datetime as date
import sqlite3 as sql3

class Block:
    def __init__(self, index, timestamp, data, previous_hash, this_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = this_hash
        
    @staticmethod
    def hash_block(index,timestamp,data,previous_hash):
        block_string = (str(index) + 
                        str(timestamp) + 
                        str(data) + 
                        str(previous_hash))
        sha = hasher.sha256()
        sha.update(block_string.encode())
        return sha.hexdigest()
    
    @classmethod
    def create_genesis_block(cls, initial_state):
        index = 0
        timestamp = date.datetime.now()
        data = [initial_state]
        previous_hash = "0"
        this_hash = Block.hash_block(index, timestamp, data, previous_hash)
        return cls(index, timestamp, data, previous_hash, this_hash)
        
    
    def check_block_hash(self):
        block_string = (str(self.index) +
                        str(self.timestamp) +
                        str(self.data) +
                        str(self.previous_hash))
        sha = hasher.sha256()
        sha.update(block_string.encode())
        
        return (sha.hexdigest() == self.hash)
    
    def check_block_validity(self, parent, state):
        #Check that each transaction is a valid update to the state
        for transaction in self.data:
            if transaction.is_valid_transaction(state):
                state = update_state(transaction, state)
            else:
                raise Exception('Invalid transaction in block %s: %s'%(self.index,transaction))
            
        if not self.check_block_hash():
            raise Exception('Hash does not match contents of block {}'.format(self.index))
        
        if self.index != (parent.index+1):
            raise Exception('Index number error on block {}: index does not match parent'.format(self.index))
        
        if self.previous_hash != parent.hash:
            raise Exception('Parent hash not accurate at block {}'.format(self.index))
        return state
    
    def block_to_db(self):
        #Inserts the block into the database
        with sql3.connect("pychaindb.db") as db:
            cursor = db.cursor()
            sql = "insert into Blockchain (blockindex, timestamp, transactions, prevhash, thishash) values (?,?,?,?,?)"
            values = (self.index, str(self.timestamp), str(self.data), str(self.previous_hash), str(self.hash))
            cursor.execute(sql, values)
            db.commit()
            
    @classmethod
    def next_block(cls, last_block, block_transactions):
        index = last_block.index + 1
        timestamp = date.datetime.now()
        data = block_transactions
        previous_hash = last_block.hash
        this_hash = Block.hash_block(index, timestamp, data, previous_hash)
        return cls(index, timestamp, data, previous_hash, this_hash)
    
class Transaction:
    def __init__(self, sender, receiver, amount):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.transaction = {self.receiver:self.amount, self.sender:(0-self.amount)}
        
    def __str__(self):
        return str(self.transaction)
    
    def __repr__(self):
        return str(self.transaction)
    
    def __eq__(self, other):
        return self.transaction == other.transaction
    
    def genesis_transaction(self, receiver, amount):
        self.sender = None
        self.receiver = receiver
        self.amount = amount
        self.transaction = {receiver:self.amount}
    
    def is_valid_transaction(self, state):
        
        
        #Checking that the transaction doesn't create or destroy tokens
        if sum(self.transaction.values()) is not 0:
            return False
        
        #Checking that the transaction doesn't overbalance an account
        for key in self.transaction.keys():
            if key in state.keys():
                balance = state[key]
                
            else:
                balance = 0
                
            if (balance + self.transaction[key]) < 0:
                return False
        return True
        
        

def update_state(transaction, state):
    # Inputs: transaction, state: dictionaries keyed with account names, holding numeric values for transfer amount (txn) or account balance (state)
    # Returns: Updated state, with additional users added to state if necessary
    # NOTE: This does not not validate the transaction- just updates the state!
    
    # If the transaction is valid, then update the state
    state = state.copy() # As dictionaries are mutable, let's avoid any confusion by creating a working copy of the data.
    for key in transaction.transaction:
        if key in state.keys():
            state[key] += transaction.transaction[key]
        else:
            state[key] = transaction.transaction[key]
    return state

def check_chain(blockchain):
    chain_state = {}
    
    for transaction in blockchain[0].data:
        chain_state = update_state(transaction, chain_state)
    blockchain[0].check_block_hash()
    parent = blockchain[0]
    
    
    for block in blockchain[1:]:
        chain_state = block.check_block_validity(parent, chain_state)
        parent = block
        
    return chain_state

def create_blockchain_table():
    with sql3.connect("pychaindb.db") as db:
        cursor = db.cursor()
        sql = "create table Blockchain (blockindex integer, timestamp text, transactions text, prevhash text, thishash text, primary key(blockindex))"
        cursor.execute(sql)
        db.commit()

def drop_blockchain_table():
    with sql3.connect("pychaindb.db") as db:
        cursor = db.cursor()
        cursor.execute("drop table if exists Blockchain")
        db.commit()



create_blockchain_table()


#Initial state of accounts, TAKE FROM DATABASE, DO NOT LEAVE AS IS
initial_transaction = Transaction(None, None, 0)
initial_transaction.genesis_transaction("Venti", 1000000000000000)
state = initial_transaction.transaction

# Create the blockchain and add the genesis block
blockchain = [Block.create_genesis_block(initial_transaction)]
previous_block = blockchain[0]
previous_block.block_to_db()

print(blockchain[0].data)

# How many blocks should we add to the chain
# after the genesis block
transactions_per_block = 3

while True:
    transaction_list = []
    
    for i in range(0, transactions_per_block):
        sender = input("Name of sender: ")
        
        if sender == "EXIT":
            break
        
        receiver = input("Name of receiver: ")
        amount = int(input("Amount to be sent: "))
        new_transaction = Transaction(sender, receiver, amount)
        
        if new_transaction.is_valid_transaction(state):
            transaction_list.append(new_transaction)
            state = update_state(new_transaction, state)
            
        else:
            print("Invalid transaction, IGNORING\n")
            
        
    if sender == "EXIT":
        break
    block_to_add = Block.next_block(previous_block, transaction_list)
    blockchain.append(block_to_add)
    previous_block = block_to_add
    block_to_add.block_to_db()
    print("Block #{} has been added to the blockchain!".format(block_to_add.index))
    print("Hash: {}\n".format(block_to_add.hash))
    print("Contents: {}".format(block_to_add.data))
    print("State is now: {}\n".format(state))
        
print(blockchain[0].index)
print(blockchain[0].timestamp)
print(blockchain[0].data)
print(blockchain[0].previous_hash)
print(blockchain[0].hash)
print("\n")
print(check_chain(blockchain))

