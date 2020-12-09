#!/usr/bin/env python
# coding: utf-8

# **Introduction**<br>
# This project is aimed to create Scroogecoin, a blockchain based cryptocurrency, in Python.

# **Design Overview**<br>
# The design has two main classes User and ScroogeCoin which will be described below.

# **Implementation**<br>
# 
# **_Used Modules:_**<br>
# 
# - fastecdsa - https://pypi.org/project/fastecdsa/<br>
# - hashlib - https://docs.python.org/3/library/hashlib.html<br>
# - json - https://docs.python.org/3/library/json.html<br>
# 
# **_Used Data structures:_**<br>
# 
# - dict - defined using {key:value, key:value, ...} or dict[key] = value. They are used in this code for blocks, transactions, and receivers. Can be interated through using dict.items() - 
#   https://docs.python.org/3/tutorial/datastructures.html#dictionaries
#   
# - lists -defined using [item, item, item] or list.append(item) as well as other ways. They are used to hold lists of blocks aka the blockchain - https://docs.python.org/3/tutorial/datastructures.html#more-on-lists

# In[ ]:


import hashlib
import json
from fastecdsa import ecdsa, keys, curve, point


# **_ScroogeCoin Class:_**<br>
# 
# - Scrooge will store the blockchain and will have the authority to create coins and accept transactions,<br>
#   put them into a block and add the block to the blockchain.
# 
# - Scrooge will contain a list to store the transaction requests and only process them<br>
#   to a block when Scrooge calls Mine function (that will be implemented in Part B).
# 
# - This should clear the transaction list and there is no limit on the number of transactions on a block.<br>
# - Each transaction will consume only a single coin but can output many.

# In[ ]:


class ScroogeCoin(object):
    def __init__(self):
        """
        Constructor
        """
        # generate a secret key (<class 'int'>) and a corresponding public key
        # (<class 'fastecdsa.point.Point'> which is an integer pair),
        # using the Bitcoin elliptic curve secp256k1 (fastecdsa.curve.secp256k1)
        self.private_key, self.public_key = keys.gen_keypair(curve.secp256k1)
        
        # create the address, or a hash of a public key, using SHA-256
        pub_key_tmp = hex(self.public_key.x << 256 | self.public_key.y).encode(encoding="utf-8")
        self.address = hashlib.sha256(pub_key_tmp).hexdigest()
        
        # list of all the blocks
        self.chain = []
        
        # list of all the current transactions (a ledger)
        self.current_transactions = []
    
    def create_hash(self, block):
        """
        Creates an SHA-256 hash of a Block
        :param block: Block
        """
        # encode the dictionary to JSON object, sort (order) to have consistent hashes
        hash_of_block = json.dumps(block, sort_keys = True, indent = 4).encode(encoding="utf-8")
        
        # compute and return hash
        return hashlib.sha256(hash_of_block).hexdigest()
    
    def sign(self, hash_):
        """
        Signs a hash
        """
        # sign 'hash_', returns two integers; 'curve' is the curve used to sign the message,
        #'hashfunc' is the hash function used to compress the message
        return ecdsa.sign(hash_, self.private_key, curve = curve.secp256k1, hashfunc = hashlib.sha256)
        
    def create_coins(self, receivers: dict):
        """
        Scrooge creates coins for any user
        
        Creates a transaction (tx) that creates coins for the Users. Hashes the tx.
        Signs the tx. Adds the tx to the transaction list which will be later mined.
        
        :param receivers: {account:amount, account:amount, ...}
        - a dictionary of input addresses and amount of coins
        """

        # create a tx
        tx = {
            "sender"    : self.address,
            # coins that are created do not come from anywhere
            "locations" : {"block" : -1, "tx" : -1, "amount" : -1}, 
            "receivers" : receivers,
        }
        
        # hash the tx
        tx["hash"] = self.create_hash(tx)
        
        # sign the hash of tx
        tx["signature"] = self.sign(tx["hash"])

        # add the tx to the transaction list
        self.current_transactions.append(tx)
 
    def get_user_tx_positions(self, address):
        """
        For a given input address, find the positions of
        all transactions where address is funded 
        
        :param address: User.address
        :return: list of all transactions where address is funded
        [{"block":block_num, "tx":tx_num, "amount":amount}, ...]
        """
        funded_transactions = []

        # for each block on the chain
        for block in self.chain:
            # initiate a counter for transactions 
            tx_index = 0
            # check all transactions stored on the current block
            for old_tx in block["transactions"]:
                # for each tx on the block read out the account (address) and the amount received
                for funded, amount in old_tx["receivers"].items():
                    # if coins were sent to the address we are interested in
                    if(address == funded):
                        # add the data about it on the list of funded transactions
                        funded_transactions.append({"block":block["index"], "tx":tx_index, "amount":amount})
                # increase the counter
                tx_index += 1

        return funded_transactions
    
    def validate_tx(self, tx, public_key):
        """
        Checks if the submitted transaction is valid:
        1. The consumed coins should be valid: the coins were created in previous transactions.
        2. Double‐spending: the consumed coins were not already consumed in some previous transaction.
        3. For the transaction, the total amount of input coins matches the total amount of output coins
           (only Scrooge can create new value).
        4. Sender's signature check: the transaction is validly signed by the owner of all the consumed coins.
        
        :param tx = {
            "sender" : User.address,
                ## a list of locations of previous transactions
                ## look at
            "locations" : {"block":block_num, "tx":tx_num, "amount":amount},
            "receivers" : {account:amount, account:amount, ...}
        }
        :param public_key: User.public_key
        :return: if tx is valid return tx
        """
        
        # verify the tx hash
        is_correct_hash = (tx["hash"] ==
                           self.create_hash({key:tx[key] for key in ['sender', 'locations', 'receivers']}))
        
        # verify the sender's signature
        is_signed = ecdsa.verify(tx["signature"], tx["hash"], public_key,
                                 curve = curve.secp256k1, hashfunc = hashlib.sha256)
                
        # check if coins were created in previous transactions
        is_funded = False
        funded_transactions = self.get_user_tx_positions(tx["sender"])
        if (tx["locations"] in funded_transactions):
            is_funded = True
        else:
            is_funded = False
        
        # check that the total value of the coins that comes out of, and came in to, the tx are equal
        amount_in = tx["locations"]["amount"]
        amount_out = sum(tx["receivers"].values())
        is_all_spent = (amount_in == amount_out)        
        
        # check on double spending: the coin was not consumed at some previous transaction in the chain
        consumed_previous = False
        # the amount of coins received by the sender in a particular block/transaction
        received_coins = self.chain[tx["locations"]["block"]]["transactions"][tx["locations"]["tx"]]["receivers"][tx["sender"]]
        # the amount of coins assigned to the sender in a particular block/transaction
        # and spent before the current tx 
        spent_coins = 0
        # for each block mined after the block where the above coins were received by the sender
        for block in self.chain[(tx["locations"]["block"] + 1):]:
            # check the list of transactions
            for transaction in block["transactions"]:
                # if a transaction belongs to the current sender
                if (transaction["sender"] == tx["sender"]):
                    # if this transaction points to the same block and transaction
                    if ((transaction["locations"]["block"] == tx["locations"]["block"]) and
                        (transaction["locations"]["tx"] == tx["locations"]["tx"])):
                        # update the value of spent coins
                        spent_coins += transaction["locations"]["amount"]
        if (tx["locations"]["amount"] <= received_coins - spent_coins):
            consumed_previous = False
        else:
            consumed_previous = True
        
        # if the transaction is valid, then add it to the transaction list
        if (is_correct_hash and is_signed and is_funded and is_all_spent and not consumed_previous):
            return tx
        else:
            # error message describing the reason why the tx was discarded
            err_msg = ""
            if not is_correct_hash:
                err_msg = "hash is invalid!"
            elif not is_signed:
                err_msg = "signature is invalid!"
            elif not is_funded:
                err_msg = "the coins were not created before!"
            elif not is_all_spent:
                err_msg = "the amounts of input and output coins do not match!"
            elif consumed_previous:
                err_msg = "double spending!"
            return err_msg
    
    def mine(self):
        """
        mines a new block onto the chain
        
        The function will take the transaction list and put all the items into a block.
        The block is hashed and signed by Scrooge and added to the blockchain. 
        Current Transaction list should be empty after mining.
        There may be a situation in which transaction list is empty.
        In that case block should be mined with empty transaction list.
        """
        
        block = {
            # if there are no blocks before, add hash of -1
            'previous_hash': self.chain[-1]["hash"] if (len(self.chain) != 0) else self.create_hash(-1),
            # the length of the chain before the current block has been processed
            'index': len(self.chain),
            'transactions': self.current_transactions
        }
        
        # hash the block
        block["hash"] = self.create_hash(block)
        
        # sign the hash of the block  
        block["signature"] = self.sign(block["hash"])
        
        # add the block to the blockchain
        self.chain.append(block)
        
        # clear the list of transactions
        self.current_transactions = []

        return block
    
    def add_tx(self, tx, public_key):
        """
        Checks that tx is valid. Adds a valid tx to current_transactions.
        Discards an invalid tx and display a message on the terminal.

        :param tx = {
            "sender" : User.address,
                ## a list of locations of previous transactions
                ## look at 
            "locations" : [{"block":block_num, "tx":tx_num, "amount":amount}, ...], 
            "receivers" : {account:amount, account:amount, ...}
        }
        :param public_key: User.public_key
        :return: True if the tx is added to current_transactions
        """
        
        #validate transaction
        tx_validated = self.validate_tx(tx, public_key)
        is_valid = (tx == tx_validated)
        
        # if tx is valid, add it to the transactions' list
        if(is_valid):
            self.current_transactions.append(tx)
            return True
        # else discard it and show a message on the terminal
        else:
            print("\nThe transaction was discarded:", tx_validated)
            return False
    
    def show_user_balance(self, address):
        """
        Computes and prints the total balance of a user address.
        
        You can scan all the chain to compute all the balance. Display the
        amount on the terminal.
        
        :param address: User.address
        """
        
        # user's balance
        balance_in = 0
        balance_out = 0
        
        # get a list of the positions of all transactions where the address was funded 
        funded_transactions = self.get_user_tx_positions(address)
        # sum all the available amounts for the user
        for pos in funded_transactions:
            balance_in += pos["amount"]
            
        # get a list of the positions where address spent money
        spent_transactions = []

        # for each block on the chain
        for block in self.chain:
            # initiate a counter for transactions 
            tx_index = 0
            # check all transactions stored on the current block
            for old_tx in block["transactions"]:
                # if sender is the address of our interest
                if (old_tx["sender"] == address):
                    # add the data about it on the list of spent transactions
                    spent_transactions.append(old_tx["locations"])
                # increase the counter
                tx_index += 1
        
        # sum all the available amounts for the user
        for pos in spent_transactions:
            balance_out += pos["amount"]
        
        print(balance_in - balance_out)
    
    def show_block(self, block_num):
        """
        Displays the contents of a block for a given block number.
        
        :param block_num: index of the block to be printed
        
        Output:
            Message's header: block number, previous hash, and signature.
            Message's body:   for each transaction on the block - transaction number, sender,
                              hash, location of the coins consumed, receiver and signature information
        """
        
        # get the length of the blockchain
        chain_length = len(self.chain)
        
        # check if the requested block is on the chain
        if block_num not in range(chain_length):
            print("\nThe requested block does not exist on the chain.")
        else:
            block = self.chain[block_num]

            # print the header
            print("\nblock:", block_num, "\n",
                  "previous hash:", block["previous_hash"], "\n",
                  "signature:", block["signature"], sep='')

            # initiate tx counter
            tx_index = 0

            # print the body
            for tx in block["transactions"]:
                # tx number, sender, hash, locations
                print("\ntx:", tx_index, "\n",
                      "sender: ", tx["sender"], "\n",                
                      "hash: ", tx["hash"], "\n",
                      "consumed coins: ",
                      "block - ", tx["locations"]["block"], ", ",
                      "tx - ", tx["locations"]["tx"], ", ",
                      "amount - ", tx["locations"]["amount"], sep='', end = '')

                # show the data on receivers
                print("\nreceivers:")
                for rec in tx["receivers"]:
                    print("account: ", rec, ", ", "ammount: ", tx["receivers"][rec], sep = '')
                # show signature
                print("signature:", tx["signature"])
                # increase tx counter
                tx_index += 1
    


# **_User Class:_**<br>
# 
# Users are only allowed to create transaction requests and forward them to Scrooge for processing.

# In[ ]:


class User(object):
    def __init__(self):
        """
        Constructor
        """
        self.private_key, self.public_key = keys.gen_keypair(curve.secp256k1)
        pub_key_tmp = hex(self.public_key.x << 256 | self.public_key.y).encode(encoding="utf-8")
        self.address = hashlib.sha256(pub_key_tmp).hexdigest()

    def create_hash(self, block):
        """
        Creates an SHA-256 hash of a Block
        :param block: Block
        """
        # encode the dictionary to JSON object, sort (order) to have consistent hashes, encode to UTF-8
        hash_of_block = json.dumps(block, sort_keys = True, indent = 4).encode(encoding="utf-8")
        
        # compute and return hash (<class 'str'>)
        hash_ = hashlib.sha256(hash_of_block).hexdigest()
        return hash_
    
    def sign(self, hash_):
        """
        Signs a hash
        """
        # sign 'hash_', returns a signature (<class 'tuple'>, contains 2 elements of <class 'int'>);
        # parameters: 'curve' is the curve used to sign the message,
        # 'hashfunc' is the hash function used to compress the message
        signature = ecdsa.sign(hash_, self.private_key, curve = curve.secp256k1, hashfunc = hashlib.sha256)
        return signature
        
    def send_tx(self, receivers, previous_tx_locations):
        """
        Creates a TX to be sent
        
        :param receivers: {account:amount, account:amount, ...}
        # location of the coins consumed
        :param previous_tx_locations: {"block" : block_num, "tx" : tx_num, "amount" : amount}
        """
        
        tx = {
                "sender"    : self.address,
                "locations" : previous_tx_locations,
                "receivers" : receivers 
             }

        # hash the tx
        tx["hash"] = self.create_hash(tx)
        
        # sign the hash of tx
        tx["signature"] = self.sign(tx["hash"])

        return tx
    


# **_A simple workflow is as follows:_**<br>
# 
# 1. Scrooge and Users create public and private keys.
# 2. Scrooge create coins for the Users, meaning it creates transactions and add it to the transaction list.
# 3. Scrooge mines the list to put the transactions into the blockchain.
# 4. Users create transactions to send coins to each other. Transactions are forwarded to Scrooge for processing.
# 5. Once Scrooge receives a transaction, it will check if the transaction is valid:
#     - If it is valid, it adds the transaction to the transaction list.<br>
#     - In case transaction is not valid, it should be discarded with displaying a message on the terminal.
# 6. Again, once Scrooge calls mine, it puts all the transactions into a block and adds it to the blockchain.<br>

# In[ ]:


# select a test case
'''
Test 0: mine a valid transaction that consumes coins from a previous block
Test 1: mine an invalid transaction where the consumed coins are invalid
Test 2: mine an invalid transaction where the consumed coins were already spent
Test 3: mine an invalid transaction where the total amounts of the input and output coins are unequal
Test 4: mine an invalid transaction where the signature is forged
'''

test = 0


# In[ ]:


def main():

    # create the central authority
    Scrooge = ScroogeCoin()
    
    # create 10 users
    users = [User() for i in range(10)]
    
    # display the balances of the users 
    print("\nInitial balances of the users:")
    for i in range(0, 10):
        print("User", i, ":", end = " ")
        Scrooge.show_user_balance(users[i].address)
    
    # central authority creates money for users 0, 1, 3, 5, 8, and 9
    Scrooge.create_coins({users[0].address:10, users[1].address:20,
                          users[3].address:50, users[5].address:15,
                          users[8].address:5, users[9].address:5})
    
    # central authority processes transaction requests and adds them to a new block onto the chain
    Scrooge.mine()
    
    # display the balances of the users
    print("\nScrooge added coins to Users 0, 1, 3, 5, 8, and 9:")
    for i in range(0, 10):
        print("User", i, ":", end = " ")
        Scrooge.show_user_balance(users[i].address)
        
    # display a block
    Scrooge.show_block(0)
    
    # choose an execution branch
    if (test == 0):
        
        # display a description of the test
        print("\n* Test 0: mine a valid transaction that consumes coins from a previous block.")
        
        # get a list of available transactions for User 0
        user_0_tx_locations = Scrooge.get_user_tx_positions(users[0].address)
        
        print("\nUser 0 sent 8 coins to himself and 2 coins to User 1.")
        
        # choose the destinations and a transaction to be consumed 
        tx = users[0].send_tx({users[1].address:2, users[0].address:8}, user_0_tx_locations[0])
        
        # validate transaction and put it on the list of transactions
        Scrooge.add_tx(tx, users[0].public_key)
        
        # mine the list to put the transactions on the blockchain
        Scrooge.mine()    
        
        # display the balances of the users
        print("\nThe balances of the users after transaction:")
        for i in range(0, 10):
            print("User", i, ":", end = " ")
            Scrooge.show_user_balance(users[i].address)
            
        print("\nDisplay block 1.")
            
        # display a block
        Scrooge.show_block(1)
        
    elif (test == 1):
        
        # display a description of the test
        print("\n* Test 1: mine an invalid transaction where the consumed coins are invalid.")
        
        # create an invalid transaction
        invalid_location = {"block" : 0, "tx" : 0, "amount" : 14}
        
        print("\nUser 0 sent 14 coins to User 3.")
        
        # choose the destinations and a transaction to be consumed 
        tx = users[0].send_tx({users[3].address:14}, invalid_location)
        
        # validate transaction and put it on the list of transactions
        Scrooge.add_tx(tx, users[0].public_key)
        
        # display the balances of the users
        print("\nThe balances of the users after transaction:")
        for i in range(0, 10):
            print("User", i, ":", end = " ")
            Scrooge.show_user_balance(users[i].address)
            
        print("\nDisplay block 1.")
            
        # display a block
        Scrooge.show_block(1)
              
    elif (test == 2):
        
        # display a description of the test
        print("\n* Test 2: mine an invalid transaction where the consumed coins were already spent.")
        
        # get a list of available transactions for User 5 and User 3
        user_3_tx_locations = Scrooge.get_user_tx_positions(users[3].address)
        user_5_tx_locations = Scrooge.get_user_tx_positions(users[5].address)
        
        print("\nUser 3 sent 25 coins to himself and 25 coins to User 2, User 5 sent 15 coins to User 1.\n")
        
        # choose the destinations and a transaction to be consumed 
        tx_3_1 = users[3].send_tx({users[3].address:25, users[2].address:25}, user_3_tx_locations[0])
        tx_5_1 = users[5].send_tx({users[1].address:15}, user_5_tx_locations[0])
        
        # validate transaction and put it on the list of transactions
        Scrooge.add_tx(tx_3_1, users[3].public_key)
        Scrooge.add_tx(tx_5_1, users[5].public_key)
        
        # mine the list to put the transactions on the blockchain
        Scrooge.mine() 
        
        # display the balances of the users
        print("\nThe balances of the users after transaction:")
        for i in range(0, 10):
            print("User", i, ":", end = " ")
            Scrooge.show_user_balance(users[i].address)
            
        # display a block
        Scrooge.show_block(1)
        
        print("\nUser 5 made an attempt to send already spent 15 coins to User 2.")
        tx_5_2 = users[5].send_tx({users[2].address:15}, user_5_tx_locations[0])
        
        # validate transaction and put it on the list of transactions
        Scrooge.add_tx(tx_5_2, users[5].public_key)
        
        # display the balances of the users
        print("\nThe balances of the users after transaction:")
        for i in range(0, 10):
            print("User", i, ":", end = " ")
            Scrooge.show_user_balance(users[i].address)
            
        print("\nDisplay block 1.")
            
        # display a block
        Scrooge.show_block(1)
        
    elif (test == 3):        
        
        # display a description of the test
        print("\n* Test 3: mine an invalid transaction where the total amounts of the in and out coins do not match.")
        
        # get a list of available transactions for User 0
        user_0_tx_locations = Scrooge.get_user_tx_positions(users[0].address)
        
        print("\nUser 0 sent 8 coins to User 1 (while the input amount was 10 coins).")
        
        # choose the destinations and a transaction to be consumed 
        tx = users[0].send_tx({users[1].address:8}, user_0_tx_locations[0])
        
        # validate transaction and put it on the list of transactions
        Scrooge.add_tx(tx, users[0].public_key) 
        
        # display the balances of the users
        print("\nThe balances of the users after transaction:")
        for i in range(0, 10):
            print("User", i, ":", end = " ")
            Scrooge.show_user_balance(users[i].address)
            
        print("\nDisplay block 1.")
            
        # display a block
        Scrooge.show_block(1)
        
    elif (test == 4):
        
        # display a description of the test
        print("\n* Test 4: mine an invalid transaction where the signature is forged.")
        
        # get a list of available transactions for User 0
        user_0_tx_locations = Scrooge.get_user_tx_positions(users[0].address)
        
        print("\nSomebody sent 10 coins to himself, pretending to be User 0, but the signature was incorrect.")
        
        # choose the destinations and a transaction to be consumed 
        tx = users[0].send_tx({users[1].address:10}, user_0_tx_locations[0])
            
        # the signature was forged
        tx["signature"] = (108442061720439793742800996113256876213579939374673738977114749281703815127415,
                           60683906192143331727711884022810909355974579518033818443695918527263393527318)
        
        # validate transaction and put it on the list of transactions
        Scrooge.add_tx(tx, users[0].public_key)
        
        # display the balances of the users
        print("\nThe balances of the users after transaction:")
        for i in range(0, 10):
            print("User", i, ":", end = " ")
            Scrooge.show_user_balance(users[i].address)
            
        print("\nDisplay block 1.")
            
        # display a block
        Scrooge.show_block(1)

    else:
        print("Choose one of the tests 0-4 and restart.")
    
if __name__ == '__main__':
    main()


# **References**<br>
# 1. Y. Doroz. ECE 579B: Blockchain and Cryptocurrencies: Assignment#1. Worcester Polytechnic Institute, 2020.
# 2. S. Goldfeder, J. Bonneau, A. Miller, A. Narayanan, E. Felten. Bitcoin and Cryptocurrency Technologies: A Comprehensive Introduction. United States: Princeton University Press, 2016.
