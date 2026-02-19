// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "forge-std/Test.sol";
import "../src/SoulToken.sol";
import "../src/BondingCurve.sol";
import "../src/SoulTokenFactory.sol";
import "../src/Treasury.sol";
import "../src/NileOracle.sol";

contract SoulTokenTest is Test {
    Treasury treasury;
    SoulTokenFactory factory;
    NileOracle oracle;

    address protocolWallet = address(0xBEEF);
    address creator = address(0xCAFE);
    address buyer = address(0xDEAD);
    address buyer2 = address(0xFACE);

    bytes16 personId = bytes16(uint128(1));

    function setUp() public {
        treasury = new Treasury(protocolWallet);
        factory = new SoulTokenFactory(payable(address(treasury)));
        oracle = new NileOracle();

        vm.deal(creator, 100 ether);
        vm.deal(buyer, 100 ether);
        vm.deal(buyer2, 100 ether);
    }

    function test_CreateSoulToken() public {
        vm.prank(creator);
        (address tokenAddr, address curveAddr) = factory.createSoulToken(
            personId,
            "LeBron Soul Token",
            "BRON"
        );

        assertTrue(tokenAddr != address(0));
        assertTrue(curveAddr != address(0));

        SoulToken token = SoulToken(tokenAddr);
        assertEq(token.name(), "LeBron Soul Token");
        assertEq(token.symbol(), "BRON");
        assertEq(token.personId(), personId);
        assertEq(token.minter(), curveAddr);
        assertEq(uint(token.phase()), uint(SoulToken.Phase.Bonding));
        assertFalse(token.graduated());
    }

    function test_CannotCreateDuplicate() public {
        vm.prank(creator);
        factory.createSoulToken(personId, "Token A", "TKA");

        vm.prank(creator);
        vm.expectRevert(SoulTokenFactory.TokenAlreadyExists.selector);
        factory.createSoulToken(personId, "Token B", "TKB");
    }

    function test_BuyViaCurve() public {
        vm.prank(creator);
        (address tokenAddr, address curveAddr) = factory.createSoulToken(
            personId, "Test Token", "TEST"
        );

        SoulToken token = SoulToken(tokenAddr);
        BondingCurve curve = BondingCurve(payable(curveAddr));

        // Buy tokens
        vm.prank(buyer);
        curve.buy{value: 1 ether}(0);

        uint256 balance = token.balanceOf(buyer);
        assertTrue(balance > 0, "Should have received tokens");

        // Check reserve increased
        assertTrue(curve.reserveBalance() > 0.01 ether, "Reserve should increase");
    }

    function test_SellViaCurve() public {
        vm.prank(creator);
        (address tokenAddr, address curveAddr) = factory.createSoulToken(
            personId, "Test Token", "TEST"
        );

        SoulToken token = SoulToken(tokenAddr);
        BondingCurve curve = BondingCurve(payable(curveAddr));

        // Buy first
        vm.prank(buyer);
        curve.buy{value: 1 ether}(0);
        uint256 tokenBalance = token.balanceOf(buyer);
        assertTrue(tokenBalance > 0);

        // Sell half
        uint256 sellAmount = tokenBalance / 2;
        uint256 ethBefore = buyer.balance;

        vm.prank(buyer);
        curve.sell(sellAmount, 0);

        assertTrue(buyer.balance > ethBefore, "Should have received ETH");
        assertEq(token.balanceOf(buyer), tokenBalance - sellAmount);
    }

    function test_PriceIncreases() public {
        vm.prank(creator);
        (address tokenAddr, address curveAddr) = factory.createSoulToken(
            personId, "Test Token", "TEST"
        );

        BondingCurve curve = BondingCurve(payable(curveAddr));

        uint256 priceBefore = curve.currentPrice();

        vm.prank(buyer);
        curve.buy{value: 1 ether}(0);

        uint256 priceAfter = curve.currentPrice();
        assertTrue(priceAfter > priceBefore, "Price should increase after buy");
    }

    function test_QuoteBuy() public {
        vm.prank(creator);
        (, address curveAddr) = factory.createSoulToken(
            personId, "Test Token", "TEST"
        );

        BondingCurve curve = BondingCurve(payable(curveAddr));
        (uint256 tokensOut, uint256 fee) = curve.quoteBuy(1 ether);

        assertTrue(tokensOut > 0, "Quote should return positive tokens");
        assertEq(fee, 0.01 ether, "Fee should be 1%");
    }

    function test_QuoteSell() public {
        vm.prank(creator);
        (address tokenAddr, address curveAddr) = factory.createSoulToken(
            personId, "Test Token", "TEST"
        );

        BondingCurve curve = BondingCurve(payable(curveAddr));

        // Buy tokens first
        vm.prank(buyer);
        curve.buy{value: 1 ether}(0);

        SoulToken token = SoulToken(tokenAddr);
        uint256 balance = token.balanceOf(buyer);

        (uint256 ethOut, uint256 fee) = curve.quoteSell(balance);
        assertTrue(ethOut > 0, "Quote should return positive ETH");
        assertTrue(fee > 0, "Fee should be positive");
    }

    function test_OnlyMinterCanMint() public {
        vm.prank(creator);
        (address tokenAddr, ) = factory.createSoulToken(
            personId, "Test Token", "TEST"
        );

        SoulToken token = SoulToken(tokenAddr);

        vm.prank(buyer);
        vm.expectRevert(SoulToken.OnlyMinter.selector);
        token.mint(buyer, 1000);
    }

    function test_FactoryTotalTokens() public {
        assertEq(factory.totalTokens(), 0);

        vm.prank(creator);
        factory.createSoulToken(personId, "Token 1", "TK1");
        assertEq(factory.totalTokens(), 1);

        bytes16 personId2 = bytes16(uint128(2));
        vm.prank(creator);
        factory.createSoulToken(personId2, "Token 2", "TK2");
        assertEq(factory.totalTokens(), 2);
    }

    function test_OracleSubmitAndVote() public {
        address agent1 = address(0x111);
        address agent2 = address(0x222);
        address agent3 = address(0x333);

        oracle.authorizeAgent(agent1);
        oracle.authorizeAgent(agent2);
        oracle.authorizeAgent(agent3);

        assertEq(oracle.agentCount(), 3);

        // Submit report
        vm.prank(agent1);
        uint256 reportId = oracle.submitReport(
            personId, "sports_win", "LeBron scores 50 points", 75
        );

        NileOracle.Report memory r = oracle.getReport(reportId);
        assertEq(r.confirmations, 1);
        assertFalse(r.finalized);

        // Second agent votes yes — should reach quorum (2/3)
        vm.prank(agent2);
        oracle.vote(reportId, true);

        r = oracle.getReport(reportId);
        assertTrue(r.finalized, "Should be finalized with 2/3 quorum");
        assertTrue(r.accepted, "Should be accepted");
        assertEq(r.impactScore, 75);
    }

    function test_OracleRejection() public {
        address agent1 = address(0x111);
        address agent2 = address(0x222);
        address agent3 = address(0x333);

        oracle.authorizeAgent(agent1);
        oracle.authorizeAgent(agent2);
        oracle.authorizeAgent(agent3);

        vm.prank(agent1);
        uint256 reportId = oracle.submitReport(
            personId, "controversy", "Fake news article", -50
        );

        // Both remaining agents reject — need 2 rejections to block quorum of 2
        vm.prank(agent2);
        oracle.vote(reportId, false);

        vm.prank(agent3);
        oracle.vote(reportId, false);

        NileOracle.Report memory r = oracle.getReport(reportId);
        assertTrue(r.finalized, "Should be finalized as rejected");
        assertFalse(r.accepted, "Should be rejected");
    }

    function test_TreasuryCreatorWithdraw() public {
        // Simulate fees via direct call
        vm.deal(address(treasury), 10 ether);
        treasury.receiveFees{value: 1 ether}(creator, 0.5 ether, 0.3 ether, 0.2 ether);

        assertEq(treasury.creatorBalances(creator), 0.5 ether);

        uint256 balBefore = creator.balance;
        vm.prank(creator);
        treasury.creatorWithdraw();

        assertEq(creator.balance, balBefore + 0.5 ether);
        assertEq(treasury.creatorBalances(creator), 0);
    }
}
