// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @title SoulToken — ERC-20 representing a person's NIL (Name, Image, Likeness) value.
/// @notice Each person in the NILE ecosystem gets exactly one SoulToken.
///         Minting/burning is restricted to the factory and bonding curve contracts.
contract SoulToken is ERC20, ERC20Permit, Ownable {
    /// @notice The person's unique identifier (matches backend Person.id).
    bytes16 public immutable personId;

    /// @notice The factory that deployed this token.
    address public immutable factory;

    /// @notice Address authorized to mint/burn (bonding curve or router).
    address public minter;

    /// @notice Current market phase.
    enum Phase { Bonding, AMM, OrderBook }
    Phase public phase;

    /// @notice Whether the token has graduated from bonding curve to AMM.
    bool public graduated;

    event PhaseChanged(Phase indexed oldPhase, Phase indexed newPhase);
    event MinterUpdated(address indexed oldMinter, address indexed newMinter);

    error OnlyMinter();
    error OnlyFactory();

    modifier onlyMinter() {
        if (msg.sender != minter) revert OnlyMinter();
        _;
    }

    modifier onlyFactory() {
        if (msg.sender != factory) revert OnlyFactory();
        _;
    }

    constructor(
        bytes16 _personId,
        string memory _name,
        string memory _symbol,
        address _factory,
        address _minter,
        address _owner
    ) ERC20(_name, _symbol) ERC20Permit(_name) Ownable(_owner) {
        personId = _personId;
        factory = _factory;
        minter = _minter;
        phase = Phase.Bonding;
    }

    /// @notice Mint tokens. Only callable by the minter (bonding curve / router).
    function mint(address to, uint256 amount) external onlyMinter {
        _mint(to, amount);
    }

    /// @notice Burn tokens. Only callable by the minter (bonding curve / router).
    function burn(address from, uint256 amount) external onlyMinter {
        _burn(from, amount);
    }

    /// @notice Update the minter address. Only callable by the factory.
    function setMinter(address newMinter) external onlyFactory {
        emit MinterUpdated(minter, newMinter);
        minter = newMinter;
    }

    /// @notice Advance the market phase. Only callable by the factory.
    function setPhase(Phase newPhase) external onlyFactory {
        emit PhaseChanged(phase, newPhase);
        phase = newPhase;
        if (newPhase == Phase.AMM) {
            graduated = true;
        }
    }
}
