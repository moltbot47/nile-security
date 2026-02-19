// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./SoulToken.sol";
import "./BondingCurve.sol";
import "./SoulTokenFactory.sol";

/// @title NileRouter — Central trade routing for Soul Tokens.
/// @notice Routes buys/sells to bonding curve (pre-graduation) or AMM (post-graduation).
///         Handles graduation flow: deploy Uniswap V3 pool, migrate liquidity, burn LP.
contract NileRouter is Ownable, ReentrancyGuard {
    SoulTokenFactory public immutable factory;

    /// @notice Uniswap V3 pool addresses after graduation (personId → pool).
    mapping(bytes16 => address) public ammPools;

    event TradeRouted(
        bytes16 indexed personId,
        address indexed trader,
        bool isBuy,
        uint256 ethAmount,
        uint256 tokenAmount
    );
    event GraduationExecuted(
        bytes16 indexed personId,
        address indexed pool,
        uint256 liquidityDeployed
    );

    error TokenNotFound();
    error NotGraduated();
    error AlreadyGraduated();

    constructor(address _factory) Ownable(msg.sender) {
        factory = SoulTokenFactory(_factory);
    }

    /// @notice Buy tokens via bonding curve.
    /// @param personId UUID of the person.
    /// @param minTokensOut Slippage protection.
    function buy(bytes16 personId, uint256 minTokensOut) external payable nonReentrant {
        (address tokenAddr, address curveAddr) = factory.getTokenPair(personId);
        SoulToken token = SoulToken(tokenAddr);

        if (token.graduated()) {
            // Post-graduation: route to AMM (future implementation)
            revert NotGraduated(); // Placeholder — AMM routing added in Sprint 5
        }

        // Route to bonding curve
        BondingCurve curve = BondingCurve(payable(curveAddr));
        uint256 balBefore = token.balanceOf(msg.sender);
        curve.buy{value: msg.value}(minTokensOut);

        // Transfer minted tokens from router to buyer
        // (tokens are minted to msg.sender of curve.buy which is this contract)
        uint256 minted = token.balanceOf(address(this));
        if (minted > 0) {
            token.transfer(msg.sender, minted);
        }

        uint256 tokensOut = token.balanceOf(msg.sender) - balBefore;
        emit TradeRouted(personId, msg.sender, true, msg.value, tokensOut);
    }

    /// @notice Sell tokens via bonding curve.
    /// @param personId UUID of the person.
    /// @param tokenAmount Amount of tokens to sell.
    /// @param minEthOut Slippage protection.
    function sell(
        bytes16 personId,
        uint256 tokenAmount,
        uint256 minEthOut
    ) external nonReentrant {
        (address tokenAddr, address curveAddr) = factory.getTokenPair(personId);
        SoulToken token = SoulToken(tokenAddr);

        if (token.graduated()) {
            revert NotGraduated(); // Placeholder for AMM routing
        }

        // Transfer tokens from seller to this contract
        token.transferFrom(msg.sender, address(this), tokenAmount);

        // Sell via bonding curve
        BondingCurve curve = BondingCurve(payable(curveAddr));
        uint256 ethBefore = address(this).balance;
        curve.sell(tokenAmount, minEthOut);
        uint256 ethReceived = address(this).balance - ethBefore;

        // Forward ETH to seller
        (bool success, ) = msg.sender.call{value: ethReceived}("");
        require(success, "ETH transfer failed");

        emit TradeRouted(personId, msg.sender, false, ethReceived, tokenAmount);
    }

    /// @notice Get a buy quote.
    function quoteBuy(bytes16 personId, uint256 ethAmount)
        external
        view
        returns (uint256 tokensOut, uint256 fee)
    {
        (, address curveAddr) = factory.getTokenPair(personId);
        return BondingCurve(payable(curveAddr)).quoteBuy(ethAmount);
    }

    /// @notice Get a sell quote.
    function quoteSell(bytes16 personId, uint256 tokenAmount)
        external
        view
        returns (uint256 ethOut, uint256 fee)
    {
        (, address curveAddr) = factory.getTokenPair(personId);
        return BondingCurve(payable(curveAddr)).quoteSell(tokenAmount);
    }

    /// @notice Allow router to receive ETH from sells.
    receive() external payable {}
}
