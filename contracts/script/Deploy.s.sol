// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "forge-std/Script.sol";
import "../src/Treasury.sol";
import "../src/SoulTokenFactory.sol";
import "../src/NileRouter.sol";
import "../src/NileOracle.sol";

/// @notice Deploy the NILE Soul Token ecosystem to Base.
contract DeployScript is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address protocolWallet = vm.envAddress("PROTOCOL_WALLET");

        vm.startBroadcast(deployerKey);

        // 1. Treasury
        Treasury treasury = new Treasury(protocolWallet);
        console.log("Treasury:", address(treasury));

        // 2. Factory
        SoulTokenFactory factory = new SoulTokenFactory(payable(address(treasury)));
        console.log("Factory:", address(factory));

        // 3. Router
        NileRouter router = new NileRouter(address(factory));
        console.log("Router:", address(router));

        // 4. Oracle
        NileOracle oracle = new NileOracle();
        console.log("Oracle:", address(oracle));

        vm.stopBroadcast();
    }
}
