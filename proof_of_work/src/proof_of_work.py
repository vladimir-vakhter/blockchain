#!/usr/bin/env python
# coding: utf-8

# **Introduction:<br>**
# This code implements the Proof of Work (PoW) functionality for a given blockchain application.<br>
# The implementation adjusts the difficulty of the PoW to match a given time interval.<br>

# **Note:<br>**
# If you want the average block creation time to be 2 seconds, even if you code it correctly, you will
# probably achieve a number between 1.5-3 seconds. It is perfectly normal given that we have a
# small runtime. As long as the timing is close enough, your code is probably correct. For instance;
# in our test for 10 second interval, we saw timings between 8 to 15 seconds.

# In[3]:


import datetime
import time
import hashlib
import random
import json
from fastecdsa import ecdsa, keys, curve, point


# In[4]:


class Miner:
    def __init__(self):
        self.chain = [] # list of all the blocks

    def genesis_block(self):
        '''
        This is the first block of the block chain
        '''
        block = {
            'previous_hash': 00000000000000,
            'index': len(self.chain),
            'transactions': [],
            'bits': 0x1EFFFFFF,        # the highest target (the lowest difficulty)
            'nonce': 0,
            'time': str(datetime.datetime.now())
        }
        return block

    def make_empty_block(self, bits):
        '''
        @param: bits is the value that is used to compute the difficulty
        as well as the target hash

        note: there is no hash in this block
        that will be added while mining
        '''
        previous_hash = self.chain[-1]['hash']
        block = {
            'previous_hash': previous_hash,
            'index': len(self.chain),
            'transactions': [],
            'bits': bits,
            'nonce': 0,
            'time' : str(datetime.datetime.now())
        }
        return block

    def calculate_hash(self, block):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        """
        # We must make sure that the Dictionary is Ordered, or we may have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    def mine(self, block):
        '''
        @param: block - this is the block that we will
        preform proof of work on

        directions:
        1) get_target_from_bits(block["bits"])
        2) hash the block
        3) if the hash of the block is not less then the value from step 1
            change the block['nonce'] and try again
        4) repeat until you find a hash that is less then the target hash
        '''
        # get the bits
        bits = block['bits']
        # get the target
        target = get_target_from_bits(bits)
        # find a hash of the block
        hash_of_block = self.calculate_hash(block)
        
        while (int(hash_of_block, 16) >= target):
            # change the nonce of the block (replace the old one in the block)
            block['nonce'] += 1
            # recalculate the hash 
            hash_of_block = self.calculate_hash(block)
        
        # add the hash to the block
        block['hash'] = hash_of_block
        
        # add the block at the end of the blockchain
        self.chain.append(block)
        return block

def pad_leading_zeros(hex_str):
    ''' 
    this function pads on the leading zeros
    this helps with readability of comparing hashes
    '''
    hex_num_chars = hex_str[2:]
    num_zeros_needed = 64 - len(hex_num_chars)
    padded_hex_str = '0x%s%s' % ('0' * num_zeros_needed, hex_num_chars)
    return padded_hex_str

def read_str_time(time):
    ''' 
    this function takes the time in string format
    and converts it to python datetime format
    '''
    return datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S.%f')

def datetime_to_seconds(time):
    ''' 
    this function takes the time in datetime format
    and returns the total number of seconds
    '''
    if(isinstance(time, datetime.datetime)):
        return int(time.timestamp())
    elif(isinstance(time, datetime.timedelta)):
        return time.total_seconds()
    else:
        print("datetime_to_seconds(time): invalid input")
    
def get_target_from_bits(bits):
    ''' 
    this function takes the bits from the block
    and expands it into a 256-bit target
    '''
    # split the bits into two parts
    part_1 = (bits & 0xFF000000) >> 24
    part_2 = (bits & 0x00FFFFFF)
    # calculate the target
    target = part_2 * 2**(8*(part_1 - 3))
    return target

def get_difficulty_from_bits(bits):
    '''
    this function calculates the bits
    '''
    difficulty_one_target = 0x00FFFFFF * 2 ** (8 * (0x1E - 3))
    target = get_target_from_bits(bits)
    calculated_difficulty = difficulty_one_target / float(target)
    return calculated_difficulty

def get_bits_from_target(target):
    '''
    this function gets the bits from the target
    this is the inverse of the get_target_from_bits()
    '''
    # target is an int --> convert it into a hex str, get the #of hex symbols, and convert it to the #of bits    
    bitlength = len(hex(target)[2:]) * 4
    # match the odd bitlength to the multiple of 8 (because we shift a 24-bit number left to the order of 8)
    if ((bitlength % 8) != 0):
        bitlength += (8 - (bitlength % 8))

    # take the left 24 bits as the header (part_2) and keep the exponent (part_1) to a minimum
    part_1 =  int(bitlength / 8)
    part_2 = target >> (8 * (part_1 - 3))
    # calculate the bits
    bits = (part_1 << 24) | part_2
    return bits

def change_target(prev_bits, start_time, end_time, target_time):
    '''
    @param prev_bits : this is previous bits value
    @param start_time : this is the starting time of this difficulty
        NOTE: type is <class 'str'>
    @param end_time : this is the end time of this difficulty
        NOTE: type is <class 'str'>
    @param target_time : this is the time that we want the blocks to take to mine

    directions:
    1) take the bits and get the target
    2) get the time_span between end and start in seconds
        NOTE: there is a function for getting datetime in seconds
    3) multiply the target by the time_span
    4) divide the target by the target time
    '''
    # get the previous target
    prev_target = get_target_from_bits(prev_bits)
    # get the time span between the last block and the first block
    time_span = int(datetime_to_seconds(read_str_time(end_time)) -
                    datetime_to_seconds(read_str_time(start_time)))
    # get the new target for the targeted time interval
    new_target = int(prev_target * time_span / target_time)
    return new_target

if __name__ == "__main__":
    '''
    this mines 144 blocks

    first it mines using difficulty 1
    then it mines and attempts to get an average time of 2 seconds
    then 4 seconds
    then 6 seconds
    and finally 10 seconds

    the average will never be exact,
    but in my testing i found it typically not off by
    more than 1 second

    NOTE: on final run for accuracy please dont run any other programs
    '''

    # the time we want each block to take (4 difficulty levels)
    times = [2, 4, 6, 10]
    # the number of blocks to mine at each difficulty level
    number_of_blocks = 32

    # create the miner
    miner = Miner()
    # create the genesis block (the first block with the given difficulty: bits = 0x1EFFFFFF)
    gen_block = miner.genesis_block()
    # mine the genesis block
    miner.mine(gen_block)

    # get the time for difficulty of 1
    for i in range(number_of_blocks):
        # get the bits
        bits = miner.chain[-1]["bits"]
        empty_block = miner.make_empty_block(bits) 
        miner.mine(empty_block)
        
    # calculate the total time for this difficulty and show it on the terminal
    totaltime = datetime_to_seconds(read_str_time(miner.chain[number_of_blocks]["time"]) -
                                    read_str_time(miner.chain[0]["time"]))
    print("average time = {}".format(totaltime/(number_of_blocks - 1)))
    print("difficulty = {}".format(get_difficulty_from_bits(bits)))

    # change the target based on the difficulty
    for index, time in enumerate(times):
        target = change_target(bits, miner.chain[index * number_of_blocks]["time"], 
                               miner.chain[(index+1) * number_of_blocks]["time"], 
                               times[index] * number_of_blocks)
        bits = get_bits_from_target(target)

        for i in range(number_of_blocks):
            empty_block = miner.make_empty_block(bits) 
            miner.mine(empty_block)

        totaltime = datetime_to_seconds(read_str_time(miner.chain[(index+2)*number_of_blocks]["time"]) - 
                                        read_str_time(miner.chain[(index+1)*number_of_blocks]["time"]))
        print("average time = {}".format(totaltime/(number_of_blocks - 1)))
        print("difficulty = {}".format(get_difficulty_from_bits(bits)))

    with open('chain.json', 'w') as outfile:
        json.dump(miner.chain, outfile, sort_keys = True, indent = 4)
        


# **References:**
# 
# https://en.bitcoin.it/wiki/Difficulty <br>
# Bitcoin Mining (Prof.Doroz)
