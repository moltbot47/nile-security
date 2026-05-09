// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "./SoulToken.sol";
import "./BondingCurve.sol";
import "./SoulTokenFactory.sol";

/// @title ISwapRouter -- Minimal interface for AMM router (Aerodrome / Uniswap V2 style).
/// @notice Only the functions we need for post-graduation swaps.
interface ISwapRouter {
    /// @notice Swap exact ETH for tokens.
    /// @param amountOutMin Minimum tokens to receive (slippage protection).
    /// @param path Token path (e.g. [WETH, token]).
    /// @param to Recipient of output tokens.
    /// @param deadline Unix timestamp after which the tx reverts.
    /// @return amounts Array of input/output amounts along the path.
    function swapExactETHForTokens(
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external payable returns (uint256[] memory amounts);

    /// @notice Swap exact tokens for ETH.
    /// @param amountIn Amount of input tokens.
    /// @param amountOutMin Minimum ETH to receive (slippage protection).
    /// @param path Token path (e.g. [token, WETH]).
    /// @param to Recipient of output ETH.
    /// @param deadline Unix timestamp after which the tx reverts.
    /// @return amounts Array of input/output amounts along the path.
    function swapExactTokensForETH(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);

    /// @notice Get the WETH address used by this router.
    function WETH() external view returns (address);
}

/// @title NileRouter -- Central trade routing for Soul Tokens.
/// @notice Routes buys/sells to bonding curve (pre-graduation) or AMM (post-graduation).
///         Handles graduation flow: deploy liquidity pool, migrate liquidity, burn LP.
contract NileRouter is Ownable, ReentrancyGuard {
    SoulTokenFactory public immutable factory;

    /// @notice AMM router used for post-graduation swaps (e.g. Aerodrome on Base).
    ISwapRouter public ammRouter;

    /// @notice Uniswap V3 / Aerodrome pool addresses after graduation (personId -> pool).
    mapping(bytes16 => address) public ammPools;

    /// @notice Default swap deadline offset in seconds (5 minutes).
    uint256 public swapDeadlineOffset = 300;

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
    event AMMRouterUpdated(address indexed oldRouter, address indexed newRouter);

    error TokenNotFound();
    error NotGraduated();
    error AlreadyGraduated();
    error AMMRouterNotSet();
    error AMMPoolNotSet();
    error SwapFailed();

    constructor(address _factory) Ownable(msg.sender) {
        factory = SoulTokenFactory(_factory);
    }

    // -----------------------------------------------------------------------
    // Admin functions
    // -----------------------------------------------------------------------

    /// @notice Set the AMM router address (Aerodrome on Base, Uniswap on other chains).
    /// @param _ammRouter Address of the V2-style swap router.
    function setAMMRouter(address _ammRouter) external onlyOwner {
        address old = address(ammRouter);
        ammRouter = ISwapRouter(_ammRouter);
        emit AMMRouterUpdated(old, _ammRouter);
    }

    /// @notice Set the AMM pool address for a graduated token.
    /// @param personId UUID of the person.
    /// @param pool Address of the liquidity pool.
    function setAMMPool(bytes16 personId, address pool) external onlyOwner {
        ammPools[personId] = pool;
    }

    /// @notice Update the default swap deadline offset.
    /// @param _offset New offset in seconds.
    function setSwapDeadlineOffset(uint256 _offset) external onlyOwner {
        swapDeadlineOffset = _offset;
    }

    // -----------------------------------------------------------------------
    // Pre-graduation: Bonding Curve trading
    // -----------------------------------------------------------------------

    /// @notice Buy tokens via bonding curve (pre-graduation) or AMM (post-graduation).
    /// @param personId UUID of the person.
    /// @param minTokensOut Slippage protection.
    function buy(bytes16 personId, uint256 minTokensOut) external payable nonReentrant {
        (address tokenAddr, address curveAddr) = factory.getTokenPair(personId);
        SoulToken token = SoulToken(tokenAddr);

        if (token.graduated()) {
            _buyGraduated(personId, tokenAddr, minTokensOut);
            return;
        }

        // Route to bonding curve
        BondingCurve curve = BondingCurve(payable(curveAddr));
        uint256 balBefore = token.balanceOf(msg.sender);
        curve.buy{value: msg.value}(minTokensOut);

        // Transfer minted tokens from router to buyer
        uint256 minted = token.balanceOf(address(this));
        if (minted > 0) {
            token.transfer(msg.sender, minted);
        }

        uint256 tokensOut = token.balanceOf(msg.sender) - balBefore;
        emit TradeRouted(personId, msg.sender, true, msg.value, tokensOut);
    }

    /// @notice Sell tokens via bonding curve (pre-graduation) or AMM (post-graduation).
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
            _sellGraduated(personId, tokenAddr, tokenAmount, minEthOut);
            return;
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

    // -----------------------------------------------------------------------
    // Post-graduation: AMM trading
    // -----------------------------------------------------------------------

    /// @notice Internal: buy tokens via AMM router after graduation.
    /// @param personId UUID of the person (for event).
    /// @param tokenAddr Address of the SoulToken.
    /// @param minTokensOut Minimum tokens to receive.
    function _buyGraduated(
        bytes16 personId,
        address tokenAddr,
        uint256 minTokensOut
    ) internal {
        if (address(ammRouter) == address(0)) revert AMMRouterNotSet();

        address weth = ammRouter.WETH();

        // Build the swap path: WETH -> Token
        address[] memory path = new address[](2);
        path[0] = weth;
        path[1] = tokenAddr;

        uint256 deadline = block.timestamp + swapDeadlineOffset;

        // Execute the swap -- sends msg.value as ETH
        uint256[] memory amounts = ammRouter.swapExactETHForTokens{value: msg.value}(
            minTokensOut,
            path,
            msg.sender,   // tokens go directly to the buyer
            deadline
        );

        uint256 tokensOut = amounts[amounts.length - 1];
        emit TradeRouted(personId, msg.sender, true, msg.value, tokensOut);
    }

    /// @notice Internal: sell tokens via AMM router after graduation.
    /// @param personId UUID of the person (for event).
    /// @param tokenAddr Address of the SoulToken.
    /// @param tokenAmount Amount of tokens to sell.
    /// @param minEthOut Minimum ETH to receive.
    function _sellGraduated(
        bytes16 personId,
        address tokenAddr,
        uint256 tokenAmount,
        uint256 minEthOut
    ) internal {
        if (address(ammRouter) == address(0)) revert AMMRouterNotSet();

        // Transfer tokens from seller to this contract
        IERC20(tokenAddr).transferFrom(msg.sender, address(this), tokenAmount);

        // Approve AMM router to spend tokens
        IERC20(tokenAddr).approve(address(ammRouter), tokenAmount);

        address weth = ammRouter.WETH();

        // Build the swap path: Token -> WETH
        address[] memory path = new address[](2);
        path[0] = tokenAddr;
        path[1] = weth;

        uint256 deadline = block.timestamp + swapDeadlineOffset;

        // Execute the swap
        uint256[] memory amounts = ammRouter.swapExactTokensForETH(
            tokenAmount,
            minEthOut,
            path,
            msg.sender,   // ETH goes directly to the seller
            deadline
        );

        uint256 ethOut = amounts[amounts.length - 1];
        emit TradeRouted(personId, msg.sender, false, ethOut, tokenAmount);
    }

    // -----------------------------------------------------------------------
    // View functions
    // -----------------------------------------------------------------------

    /// @notice Get a buy quote (bonding curve only -- AMM quotes use the AMM directly).
    function quoteBuy(bytes16 personId, uint256 ethAmount)
        external
        view
        returns (uint256 tokensOut, uint256 fee)
    {
        (, address curveAddr) = factory.getTokenPair(personId);
        return BondingCurve(payable(curveAddr)).quoteBuy(ethAmount);
    }

    /// @notice Get a sell quote (bonding curve only -- AMM quotes use the AMM directly).
    function quoteSell(bytes16 personId, uint256 tokenAmount)
        external
        view
        returns (uint256 ethOut, uint256 fee)
    {
        (, address curveAddr) = factory.getTokenPair(personId);
        return BondingCurve(payable(curveAddr)).quoteSell(tokenAmount);
    }

    /// @notice Check whether a token has graduated to AMM trading.
    /// @param personId UUID of the person.
    /// @return graduated True if the token has graduated.
    /// @return pool Address of the AMM pool (zero if not set yet).
    function graduationStatus(bytes16 personId)
        external
        view
        returns (bool graduated, address pool)
    {
        (address tokenAddr, ) = factory.getTokenPair(personId);
        graduated = SoulToken(tokenAddr).graduated();
        pool = ammPools[personId];
    }

    /// @notice Allow router to receive ETH from sells.
    receive() external payable {}
}
