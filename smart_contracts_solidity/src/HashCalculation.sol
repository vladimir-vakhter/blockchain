pragma solidity ^0.4.22;

contract HashCalc
{
    // pure functions ensure that they use only their parameters without any side effects
    /*
     * _bid, in USD, specifies how much money should be sent.
     * _seed is any random (unique) number to prevent replay attacks.
     * _public_key is the address of the caller
    */
    function getHash(uint _bid, uint _seed, address _public_key) public pure returns (bytes32) {
        return sha256(abi.encode(_bid, _seed, _public_key));
    }
}
