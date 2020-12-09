pragma solidity ^0.4.22;

// the interface to the contract that calculates the hash of commit
contract HashCalc
{
    function getHash(uint, uint, address) public pure returns (bytes32) {}
}

// the interface to the contract that receives the exchange rate USD/ETH
contract EthUsd
{
    function updatePrice() public payable {}
    function getExchRate() public pure returns(uint) {}
}

// auction
contract Auction {

    // ------------------------------------------user data types-------------------------------------------------- 
    
    // the person who enters an auction and makes a bid (EOA account)
    struct Auctioneer {
        bool        registered;     
        bool        bidCommitted;         
        bytes32     commitment;     // hash of (bid in USD, random seed, public key)
        uint        valueWei;       // the value in Wei associated with the commitment
                                    // 1 Ether = 1,000,000,000,000,000,000 Wei (10^18) 
        uint        bidUsd;         // the value of the bid in USD
        bool        bidSent;
        bool        bidValid;
    }

    // ------------------------------------------private parameters------------------------------------------------  
      
    // keep track of auctioneers
    mapping(address => Auctioneer) auctioneers;
    
    // a dynamic array of the addresses of auctioneers (is needed to 'parse' the stored data)
    address[] auctioneer_addresses;
    
    // hash calculation
    HashCalc hashCalc;
    
    // exchange rate query
    EthUsd ethUsdQuery;
    
    // -----------------------------------------public parameters--------------------------------------------------
    
    // the owner of this contract
    address public owner;

    // exchange rate
    uint public ETHUSD;
    
    // total number of auctioneer                       
    uint public totalAuctioneers;       
    
    // status of registration (open/closed)             
    bool public registrationClosed;
    
    // status of commitments (open/closed)                         
    bool public commitmentClosed;

    // a winner list
    address[] public winners;

    // total number of committed bids                   
    uint public totalBidsCommitted;
    
    // total number of sent bids
    uint public totalBidsSent;

    // -----------------------------------------public methods-----------------------------------------------------

    // constructor
    constructor () public {
        owner = msg.sender;
    }

    // register an auctioneer
    function registerAuctioneer(address _person) public {
        // the registration is opened
        require(!registrationClosed);
        // the auctioneer is not registered
        require(!auctioneers[msg.sender].registered);
        // update the status of the auctioneer
        auctioneers[_person].registered = true;
        // update service data
        auctioneer_addresses.push(_person);
        totalAuctioneers += 1;
    }

    function computeHash(uint _bid, uint _seed) public view returns (bytes32) {
        return hashCalc.getHash(_bid, _seed, msg.sender);
    }

    // commit a bid (payable, because an auctioneer should add the value in Weis that is larger than his bid in USD)
    function commitBid(bytes32 _hash_commit) public payable {
        // the commitment is opened
        require(!commitmentClosed);
        // the auctioneer is registered and did not bid
        require(auctioneers[msg.sender].registered);
        require(!auctioneers[msg.sender].bidCommitted);

        // store the commitment
        auctioneers[msg.sender].commitment = _hash_commit;
        // store the value in wei
        auctioneers[msg.sender].valueWei = msg.value;
        // update service data
        auctioneers[msg.sender].bidCommitted = true;
        totalBidsCommitted += 1;
    }
    
    // send a bid
    function sendBid(uint _bid, uint _seed) public {
        // the auctioneer did not send a bid before
        require(!auctioneers[msg.sender].bidSent);
        // update the service data
        auctioneers[msg.sender].bidSent = true;
        // verify the commitment        
        bytes32 hash = hashCalc.getHash(_bid, _seed, msg.sender);
        if (hash == auctioneers[msg.sender].commitment) {
            // the contract received the correct bidding value
            auctioneers[msg.sender].bidValid = true;
            // store its value in USD
            auctioneers[msg.sender].bidUsd = _bid;
        }
        totalBidsSent += 1;
    }
    
    // -----------------------------------------private methods----------------------------------------------------
    
    // a modifier that checks the input condition
    modifier ownerOnly() {
        require(msg.sender == owner);
        // represents the remaining body of the modified function
        _;                                  
    }
    
    // assign the address of the contract that calculates the hashes of commitments
    function hashCalcExistAt(address _addr) ownerOnly public {
        hashCalc = HashCalc(_addr);
    }

    // assign the address of the contract that queries the exchange rate
    function ethUsdExistAt(address _addr) ownerOnly public {
        ethUsdQuery = EthUsd(_addr);
    }

    // stop registration
    function registerStop() ownerOnly public {
        registrationClosed = true;
    }
    
    // stop commitment
    function commitBidStop() ownerOnly public {
        commitmentClosed = true;
    }

    // request the last exchange rate USD/Ethereum using an oracle
    function computeExchange() ownerOnly public payable {
        ethUsdQuery.updatePrice();
    }

    // get the last updated exchange rate
    function getExchRate() public returns(uint) {
        ETHUSD = ethUsdQuery.getExchRate();
    }

    // compute the winner
    function computeWinner() ownerOnly public payable {
        // if each auctioneer committed a bid or if the commitment is closed
        if ((totalAuctioneers == totalBidsCommitted) || commitmentClosed) {

            // the winner
            address win_addr;
            
            // check all the bids and find the maximum valid among them
            for (uint i = 0; i < auctioneer_addresses.length; i++) {
                // take the address
                address addr = auctioneer_addresses[i];
                // check if a bid was sent and if it is valid
                if (auctioneers[addr].bidSent && auctioneers[addr].bidValid) {
                    // check if the value in Wei is more than the value in USD
                    if (auctioneers[addr].valueWei > uint(auctioneers[addr].bidUsd / ETHUSD * 10**18)) {
                        if (i == 0) {
                            win_addr = addr;
                        } else {
                            // if the bid in USD of the current address is bigger than the previously found biggest bid in USD  
                            if (auctioneers[addr].bidUsd > auctioneers[win_addr].bidUsd) {
                                // return money to the address with the previously found biggest bid in USD 
                                win_addr.transfer(auctioneers[win_addr].valueWei);
                                // update the winner address
                                win_addr = addr;
                            } else {
                                // return money since it is a completely valid bid, but not the biggest one
                                addr.transfer(auctioneers[addr].valueWei);   
                            }
                        }
                    } else {
                        // bid is invalid and the value will be seized
                        auctioneers[addr].bidValid = false;
                    }
                }
            }
            
            // add the winner to the winner list
            winners.push(win_addr);
            
            // return the overhead to the winner
            uint win_overhead = auctioneers[win_addr].valueWei - uint(auctioneers[win_addr].bidUsd / ETHUSD * 10**18);
            win_addr.transfer(win_overhead);
        }
    }
    
    // reset the auction
    function resetAuction() ownerOnly public {
        // clean the mapping
        for (uint i = 0; i < auctioneer_addresses.length; i++) {
            delete auctioneers[auctioneer_addresses[i]];
        }
        // clean the array of addresses
        delete auctioneer_addresses;
        
        // reset parameters
        ETHUSD = 0;
        totalAuctioneers = 0;
        registrationClosed = false;
        commitmentClosed = false;
        totalBidsCommitted = 0;
        totalBidsSent = 0;
    }
}

