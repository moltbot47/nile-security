// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./SoulToken.sol";
import "./BondingCurve.sol";
import "./Treasury.sol";

/// @title SoulTokenFactory — Deploys SoulToken + BondingCurve pairs via CREATE2.
/// @notice Central registry mapping personId to token and curve addresses.
contract SoulTokenFactory is Ownable {
    struct TokenPair {
        address token;
        address curve;
        address creator;
        bool exists;
    }

    /// @notice Treasury contract for fee distribution.
    Treasury public immutable treasury;

    /// @notice Default graduation threshold in ETH.
    uint256 public defaultGraduationThreshold = 20 ether;

    /// @notice Registry: personId → TokenPair
    mapping(bytes16 => TokenPair) public registry;

    /// @notice All deployed person IDs.
    bytes16[] public deployedPersonIds;

    event SoulTokenCreated(
        bytes16 indexed personId,
        address indexed token,
        address indexed curve,
        address creator,
        string name,
        string symbol
    );
    event GraduationThresholdUpdated(uint256 oldThreshold, uint256 newThreshold);

    error TokenAlreadyExists();
    error TokenNotFound();

    constructor(address payable _treasury) Ownable(msg.sender) {
        treasury = Treasury(_treasury);
    }

    /// @notice Deploy a new SoulToken + BondingCurve pair.
    /// @param personId UUID of the person (from backend).
    /// @param name Token name (e.g. "LeBron James Soul Token").
    /// @param symbol Token symbol (e.g. "BRON").
    function createSoulToken(
        bytes16 personId,
        string calldata name,
        string calldata symbol
    ) external returns (address tokenAddr, address curveAddr) {
        if (registry[personId].exists) revert TokenAlreadyExists();

        // Deploy SoulToken via CREATE2 for deterministic addresses
        bytes32 salt = bytes32(personId);
        SoulToken token = new SoulToken{salt: salt}(
            personId,
            name,
            symbol,
            address(this), // factory
            address(0),    // minter set after curve deploy
            owner()        // owner
        );

        // Deploy BondingCurve
        BondingCurve curve = new BondingCurve{salt: salt}(
            address(token),
            payable(address(treasury)),
            msg.sender,
            defaultGraduationThreshold
        );

        // Set curve as minter
        token.setMinter(address(curve));

        // Register
        registry[personId] = TokenPair({
            token: address(token),
            curve: address(curve),
            creator: msg.sender,
            exists: true
        });
        deployedPersonIds.push(personId);

        emit SoulTokenCreated(personId, address(token), address(curve), msg.sender, name, symbol);
        return (address(token), address(curve));
    }

    /// @notice Look up token/curve for a person.
    function getTokenPair(bytes16 personId) external view returns (address token, address curve) {
        TokenPair storage pair = registry[personId];
        if (!pair.exists) revert TokenNotFound();
        return (pair.token, pair.curve);
    }

    /// @notice Total number of deployed tokens.
    function totalTokens() external view returns (uint256) {
        return deployedPersonIds.length;
    }

    /// @notice Update default graduation threshold. Owner only.
    function setGraduationThreshold(uint256 newThreshold) external onlyOwner {
        emit GraduationThresholdUpdated(defaultGraduationThreshold, newThreshold);
        defaultGraduationThreshold = newThreshold;
    }

    /// @notice Graduate a token: update phase, transfer minter to router.
    /// @dev Called by NileRouter during graduation flow.
    function graduateToken(bytes16 personId, address newMinter) external onlyOwner {
        TokenPair storage pair = registry[personId];
        if (!pair.exists) revert TokenNotFound();

        SoulToken(pair.token).setPhase(SoulToken.Phase.AMM);
        SoulToken(pair.token).setMinter(newMinter);
    }
}
