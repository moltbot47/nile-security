// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "forge-std/Script.sol";
import "../src/Treasury.sol";
import "../src/SoulTokenFactory.sol";
import "../src/NileRouter.sol";
import "../src/NileOracle.sol";

/// @notice Deploy the NILE Soul Token ecosystem to Base Sepolia.
contract DeployScript is Script {
    function run() external {
        uint256 deployerKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerKey);
        
        // Use deployer as protocol wallet if PROTOCOL_WALLET not set
        address protocolWallet;
        try vm.envAddress("PROTOCOL_WALLET") returns (address pw) {
            protocolWallet = pw;
        } catch {
            protocolWallet = deployer;
        }

        console.log("Deployer:", deployer);
        console.log("Protocol Wallet:", protocolWallet);

        vm.startBroadcast(deployerKey);

        // 1. Treasury — collects and distributes fees
        Treasury treasury = new Treasury(protocolWallet);
        console.log("Treasury:", address(treasury));

        // 2. Factory — deploys SoulToken + BondingCurve pairs
        SoulTokenFactory factory = new SoulTokenFactory(payable(address(treasury)));
        console.log("Factory:", address(factory));

        // 3. Router — routes trades to bonding curves
        NileRouter router = new NileRouter(address(factory));
        console.log("Router:", address(router));

        // 4. Oracle — consensus oracle for NIL events
        NileOracle oracle = new NileOracle();
        console.log("Oracle:", address(oracle));

        // 5. Post-deploy: authorize deployer as oracle agent
        oracle.authorizeAgent(deployer);
        console.log("Oracle agent authorized:", deployer);

        vm.stopBroadcast();

        // Summary
        console.log("\n=== DEPLOYMENT SUMMARY ===");
        console.log("Chain: Base Sepolia (84532)");
        console.log("Treasury:", address(treasury));
        console.log("SoulTokenFactory:", address(factory));
        console.log("NileRouter:", address(router));
        console.log("NileOracle:", address(oracle));
        console.log("=========================");
    }
}
