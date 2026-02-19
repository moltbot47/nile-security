// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/// @title Treasury — Fee collection and distribution for the NILE ecosystem.
/// @notice Collects fees from bonding curves, splits between creator/protocol/stakers.
contract Treasury is Ownable, ReentrancyGuard {
    /// @notice Protocol wallet for protocol fees.
    address public protocolWallet;

    /// @notice Accumulated creator balances (creator address → balance).
    mapping(address => uint256) public creatorBalances;

    /// @notice Total staker fees accumulated (distributed separately).
    uint256 public stakerPool;

    /// @notice Total protocol fees collected.
    uint256 public totalProtocolFees;
    /// @notice Total creator fees collected.
    uint256 public totalCreatorFees;
    /// @notice Total staker fees collected.
    uint256 public totalStakerFees;

    event FeesReceived(
        address indexed creator,
        uint256 creatorFee,
        uint256 protocolFee,
        uint256 stakerFee
    );
    event CreatorWithdraw(address indexed creator, uint256 amount);
    event ProtocolWithdraw(address indexed wallet, uint256 amount);
    event StakerDistribution(uint256 amount);
    event ProtocolWalletUpdated(address indexed oldWallet, address indexed newWallet);

    error InsufficientBalance();
    error TransferFailed();
    error ZeroAddress();

    constructor(address _protocolWallet) Ownable(msg.sender) {
        if (_protocolWallet == address(0)) revert ZeroAddress();
        protocolWallet = _protocolWallet;
    }

    /// @notice Receive fees from a bonding curve.
    /// @dev Called by BondingCurve._distributeFee via low-level call.
    function receiveFees(
        address creator,
        uint256 creatorFee,
        uint256 protocolFee,
        uint256 stakerFee
    ) external payable {
        creatorBalances[creator] += creatorFee;
        totalCreatorFees += creatorFee;
        totalProtocolFees += protocolFee;
        stakerPool += stakerFee;
        totalStakerFees += stakerFee;

        emit FeesReceived(creator, creatorFee, protocolFee, stakerFee);
    }

    /// @notice Creator withdraws accumulated fees.
    function creatorWithdraw() external nonReentrant {
        uint256 balance = creatorBalances[msg.sender];
        if (balance == 0) revert InsufficientBalance();

        creatorBalances[msg.sender] = 0;
        (bool success, ) = msg.sender.call{value: balance}("");
        if (!success) revert TransferFailed();

        emit CreatorWithdraw(msg.sender, balance);
    }

    /// @notice Withdraw protocol fees to protocol wallet. Owner only.
    function protocolWithdraw() external onlyOwner nonReentrant {
        uint256 balance = totalProtocolFees;
        if (balance == 0) revert InsufficientBalance();

        totalProtocolFees = 0;
        (bool success, ) = protocolWallet.call{value: balance}("");
        if (!success) revert TransferFailed();

        emit ProtocolWithdraw(protocolWallet, balance);
    }

    /// @notice Update protocol wallet address. Owner only.
    function setProtocolWallet(address newWallet) external onlyOwner {
        if (newWallet == address(0)) revert ZeroAddress();
        emit ProtocolWalletUpdated(protocolWallet, newWallet);
        protocolWallet = newWallet;
    }

    /// @notice Allow treasury to receive ETH.
    receive() external payable {}
}
