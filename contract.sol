pragma solidity >=0.4.21 <0.6.0;

contract SimpleStorage {
  uint public storedData;

  constructor() public {
    storedData = 10;
  }

  function set(uint x) public {
    storedData = x;        // uses ~26691 gas
  }

  function get() public view returns (uint retVal) {
    return storedData;
  }
}

