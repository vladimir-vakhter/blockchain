// 'oraclize' was renamed to 'provable': https://docs.provable.xyz/
// Plugins to be used: Compiler, Deploy & Run, Provable
// Tutorial: https://www.youtube.com/watch?v=v2Skr_m0J2E

pragma solidity ^0.4.22;

// import provable API
import "github.com/provable-things/ethereum-api/provableAPI_0.4.25.sol";
// or, for the latest stable Solidity compiler, import "github.com/provable-things/ethereum-api/provableAPI.sol"; 

// This contract fetches the last ETH/USD from Coinbase Pro APIs
contract EthUsd is usingProvable {

   // exchange rate 
   uint ETHUSD;

   // triggering events (events are for the outside world only, like web3)
   event NewProvableQuery(string description);
   event PriceUpdated(string price);
   
   // the function executed by the transaction
   function __callback(bytes32 myid, string result) {
       if (msg.sender != provable_cbAddress()) revert();
       ETHUSD = parseInt(result);   // in fact the price is float, and parseInt() rounds it down
                                    // (e.g, for 214.97USD per 1Eth, the rounded value will be 214)
       PriceUpdated(result);
   }

   // send a query to update the price of Ether
   function updatePrice() payable {
       if (provable_getPrice("URL") > this.balance) {
           NewProvableQuery("Provable query was NOT sent, please add some ETH to cover for the query fee");
       } else {
           NewProvableQuery("Provable query was sent, standing by for the answer..");
           provable_query("URL", "json(https://api.pro.coinbase.com/products/ETH-USD/ticker).price");
       }
   }
   
   // getter
   function getExchRate() public view returns(uint) {
       return ETHUSD;
   }
}

