// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./SoulToken.sol";
import "./Treasury.sol";

/// @title BondingCurve — Bancor continuous token model for Soul Tokens.
/// @notice Implements buy/sell with a ~33.3% reserve ratio.
///         Graduation triggers when reserve balance exceeds threshold.
///
///  Buy formula:  tokensOut = supply * ((1 + ethIn / reserve) ^ (ratio / 1e6) - 1)
///  Sell formula: ethOut    = reserve * (1 - (1 - tokensIn / supply) ^ (1e6 / ratio))
///
///  For gas efficiency, we use a linear approximation for small trades and
///  a piece-wise power function for larger ones.
contract BondingCurve is ReentrancyGuard {
    /// @notice Reserve ratio in PPM (parts per million). 333333 ≈ 33.3%.
    uint32 public constant RESERVE_RATIO = 333_333;
    uint32 public constant PPM = 1_000_000;

    /// @notice Fee in basis points (100 = 1%).
    uint16 public constant FEE_BPS = 100;
    uint16 public constant FEE_CREATOR_BPS = 50;   // 0.5%
    uint16 public constant FEE_PROTOCOL_BPS = 30;  // 0.3%
    uint16 public constant FEE_STAKER_BPS = 20;    // 0.2%

    /// @notice Initial virtual reserve to keep buy/sell approximations accurate.
    uint256 public constant INITIAL_RESERVE = 10 ether;
    /// @notice Initial virtual supply.
    uint256 public constant INITIAL_SUPPLY = 100_000 ether; // 100k virtual tokens

    SoulToken public immutable token;
    Treasury public immutable treasury;
    address public immutable creator;

    /// @notice ETH reserve balance held by this curve.
    uint256 public reserveBalance;

    /// @notice Graduation threshold in ETH. When reserve exceeds this, token can graduate.
    uint256 public graduationThreshold;

    /// @notice Whether this curve is still active (not graduated).
    bool public active;

    event Buy(
        address indexed buyer,
        uint256 ethIn,
        uint256 tokensOut,
        uint256 fee,
        uint256 newPrice
    );
    event Sell(
        address indexed seller,
        uint256 tokensIn,
        uint256 ethOut,
        uint256 fee,
        uint256 newPrice
    );
    event GraduationTriggered(uint256 reserveBalance);

    error CurveNotActive();
    error InsufficientPayment();
    error InsufficientTokens();
    error SlippageExceeded();
    error TransferFailed();

    constructor(
        address _token,
        address payable _treasury,
        address _creator,
        uint256 _graduationThreshold
    ) {
        token = SoulToken(_token);
        treasury = Treasury(_treasury);
        creator = _creator;
        graduationThreshold = _graduationThreshold;
        reserveBalance = INITIAL_RESERVE;
        active = true;
    }

    /// @notice Buy tokens by sending ETH.
    /// @param minTokensOut Minimum tokens expected (slippage protection).
    function buy(uint256 minTokensOut) external payable nonReentrant {
        if (!active) revert CurveNotActive();
        if (msg.value == 0) revert InsufficientPayment();

        // Deduct fee
        uint256 fee = (msg.value * FEE_BPS) / 10_000;
        uint256 ethAfterFee = msg.value - fee;

        // Calculate tokens to mint
        uint256 supply = _effectiveSupply();
        uint256 tokensOut = _calculateBuy(supply, reserveBalance, ethAfterFee);
        if (tokensOut < minTokensOut) revert SlippageExceeded();

        // Update state
        reserveBalance += ethAfterFee;

        // Mint tokens to buyer
        token.mint(msg.sender, tokensOut);

        // Distribute fees
        _distributeFee(fee);

        uint256 newPrice = _currentPrice();
        emit Buy(msg.sender, msg.value, tokensOut, fee, newPrice);

        // Check graduation
        if (reserveBalance >= graduationThreshold) {
            active = false;
            emit GraduationTriggered(reserveBalance);
        }
    }

    /// @notice Sell tokens for ETH.
    /// @param tokenAmount Tokens to sell.
    /// @param minEthOut Minimum ETH expected (slippage protection).
    function sell(uint256 tokenAmount, uint256 minEthOut) external nonReentrant {
        if (!active) revert CurveNotActive();
        if (tokenAmount == 0) revert InsufficientTokens();

        uint256 supply = _effectiveSupply();
        uint256 ethOut = _calculateSell(supply, reserveBalance, tokenAmount);

        // Deduct fee
        uint256 fee = (ethOut * FEE_BPS) / 10_000;
        uint256 ethAfterFee = ethOut - fee;
        if (ethAfterFee < minEthOut) revert SlippageExceeded();

        // Update state
        reserveBalance -= ethOut;

        // Burn tokens from seller
        token.burn(msg.sender, tokenAmount);

        // Send ETH to seller
        (bool success, ) = msg.sender.call{value: ethAfterFee}("");
        if (!success) revert TransferFailed();

        // Distribute fees
        _distributeFee(fee);

        uint256 newPrice = _currentPrice();
        emit Sell(msg.sender, tokenAmount, ethAfterFee, fee, newPrice);
    }

    /// @notice Get current token price in ETH (per 1 token).
    function currentPrice() external view returns (uint256) {
        return _currentPrice();
    }

    /// @notice Quote a buy: how many tokens for a given ETH amount.
    function quoteBuy(uint256 ethAmount) external view returns (uint256 tokensOut, uint256 fee) {
        fee = (ethAmount * FEE_BPS) / 10_000;
        uint256 ethAfterFee = ethAmount - fee;
        tokensOut = _calculateBuy(_effectiveSupply(), reserveBalance, ethAfterFee);
    }

    /// @notice Quote a sell: how much ETH for a given token amount.
    function quoteSell(uint256 tokenAmount) external view returns (uint256 ethOut, uint256 fee) {
        uint256 grossEth = _calculateSell(_effectiveSupply(), reserveBalance, tokenAmount);
        fee = (grossEth * FEE_BPS) / 10_000;
        ethOut = grossEth - fee;
    }

    // --- Internal ---

    function _effectiveSupply() internal view returns (uint256) {
        return token.totalSupply() + INITIAL_SUPPLY;
    }

    function _currentPrice() internal view returns (uint256) {
        // Price per token (in wei per 1e18 token-units)
        // = reserve / (supply * reserveRatio/PPM)
        // = (reserve * PPM * 1e18) / (supply * RESERVE_RATIO)
        uint256 supply = _effectiveSupply();
        if (supply == 0) return 0;
        return (reserveBalance * PPM) / (supply * RESERVE_RATIO / 1e18);
    }

    /// @notice Bancor buy formula with linear approximation.
    ///  tokensOut = supply * ((1 + ethIn / reserve)^(ratio/PPM) - 1)
    ///  Using: (1+x)^n ≈ 1 + n*x for small x (x < 0.1)
    ///  For larger x, use quadratic: 1 + n*x + n*(n-1)*x^2/2
    function _calculateBuy(
        uint256 supply,
        uint256 reserve,
        uint256 ethIn
    ) internal pure returns (uint256) {
        if (reserve == 0 || supply == 0) return 0;

        // x = ethIn / reserve (scaled by 1e18)
        uint256 x = (ethIn * 1e18) / reserve;
        // n = RESERVE_RATIO / PPM (scaled by 1e18) = 333333 * 1e18 / 1e6
        uint256 n = (uint256(RESERVE_RATIO) * 1e18) / PPM;

        uint256 result;
        if (x < 0.1e18) {
            // Linear: supply * n * x / 1e18
            result = (supply * n / 1e18) * x / 1e18;
        } else {
            // Quadratic: supply * (n*x + n*(n-1)*x^2 / (2*1e18)) / 1e18
            uint256 nx = (n * x) / 1e18;
            uint256 nMinus1 = n > 1e18 ? n - 1e18 : 0;
            uint256 x2 = (x * x) / 1e18;
            uint256 quadTerm = (n * nMinus1 / 1e18) * x2 / (2 * 1e18);
            result = (supply * (nx + quadTerm)) / 1e18;
        }
        return result;
    }

    /// @notice Bancor sell formula with linear approximation.
    ///  ethOut = reserve * (1 - (1 - tokensIn / supply)^(PPM/ratio))
    function _calculateSell(
        uint256 supply,
        uint256 reserve,
        uint256 tokensIn
    ) internal pure returns (uint256) {
        if (supply == 0 || reserve == 0 || tokensIn == 0) return 0;
        if (tokensIn >= supply) return reserve; // sell everything

        // x = tokensIn / supply (scaled by 1e18)
        uint256 x = (tokensIn * 1e18) / supply;
        // n = PPM / RESERVE_RATIO (scaled by 1e18) = 1e6 * 1e18 / 333333 ≈ 3e18
        uint256 n = (uint256(PPM) * 1e18) / RESERVE_RATIO;

        uint256 result;
        if (x < 0.1e18) {
            // Linear: reserve * n * x / 1e18
            result = (reserve * n / 1e18) * x / 1e18;
        } else {
            // Quadratic: reserve * (n*x - n*(n-1)*x^2 / (2*1e18)) / 1e18
            uint256 nx = (n * x) / 1e18;
            uint256 nMinus1 = n > 1e18 ? n - 1e18 : 0;
            uint256 x2 = (x * x) / 1e18;
            uint256 quadTerm = (n * nMinus1 / 1e18) * x2 / (2 * 1e18);
            result = (reserve * (nx - quadTerm)) / 1e18;
        }

        // Never return more than reserve
        return result > reserve ? reserve : result;
    }

    function _distributeFee(uint256 fee) internal {
        if (fee == 0) return;
        uint256 creatorFee = (fee * FEE_CREATOR_BPS) / FEE_BPS;
        uint256 protocolFee = (fee * FEE_PROTOCOL_BPS) / FEE_BPS;
        uint256 stakerFee = fee - creatorFee - protocolFee;

        // Send to treasury for distribution
        (bool success, ) = address(treasury).call{value: fee}(
            abi.encodeWithSelector(
                Treasury.receiveFees.selector,
                creator,
                creatorFee,
                protocolFee,
                stakerFee
            )
        );
        // Silently handle failure — fees are not critical path
        if (!success) {
            // Keep fees in curve as extra reserve
            reserveBalance += fee;
        }
    }

    /// @notice Allow curve to receive ETH (for initial seeding).
    receive() external payable {
        reserveBalance += msg.value;
    }
}
