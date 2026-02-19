// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import "@openzeppelin/contracts/access/Ownable.sol";

/// @title NileOracle — On-chain consensus oracle for person NIL events.
/// @notice Authorized oracle agents submit reports about real-world events
///         (social media, news, sports results, etc.). Quorum of 2/3 required.
contract NileOracle is Ownable {
    struct Report {
        bytes16 personId;
        string eventType;
        string headline;
        int16 impactScore;   // -100 to +100
        uint8 confirmations;
        uint8 rejections;
        uint8 requiredQuorum;
        bool finalized;
        bool accepted;
        address submitter;
        uint48 submittedAt;
    }

    /// @notice Authorized oracle agent wallets.
    mapping(address => bool) public authorizedAgents;
    uint256 public agentCount;

    /// @notice Reports indexed by ID.
    mapping(uint256 => Report) public reports;
    uint256 public reportCount;

    /// @notice Track which agents have voted on which reports.
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    event AgentAuthorized(address indexed agent);
    event AgentRevoked(address indexed agent);
    event ReportSubmitted(uint256 indexed reportId, bytes16 indexed personId, address submitter);
    event VoteCast(uint256 indexed reportId, address indexed agent, bool approve);
    event ReportFinalized(uint256 indexed reportId, bool accepted, int16 impactScore);

    error NotAuthorized();
    error AlreadyVoted();
    error AlreadyFinalized();
    error InvalidImpactScore();

    modifier onlyAgent() {
        if (!authorizedAgents[msg.sender]) revert NotAuthorized();
        _;
    }

    constructor() Ownable(msg.sender) {}

    /// @notice Authorize an oracle agent wallet.
    function authorizeAgent(address agent) external onlyOwner {
        if (!authorizedAgents[agent]) {
            authorizedAgents[agent] = true;
            agentCount++;
            emit AgentAuthorized(agent);
        }
    }

    /// @notice Revoke an oracle agent wallet.
    function revokeAgent(address agent) external onlyOwner {
        if (authorizedAgents[agent]) {
            authorizedAgents[agent] = false;
            agentCount--;
            emit AgentRevoked(agent);
        }
    }

    /// @notice Submit a new oracle report.
    function submitReport(
        bytes16 personId,
        string calldata eventType,
        string calldata headline,
        int16 impactScore
    ) external onlyAgent returns (uint256 reportId) {
        if (impactScore < -100 || impactScore > 100) revert InvalidImpactScore();

        reportId = reportCount++;
        uint8 quorum = uint8((agentCount * 2 + 2) / 3); // ceil(2/3)
        if (quorum < 1) quorum = 1;

        reports[reportId] = Report({
            personId: personId,
            eventType: eventType,
            headline: headline,
            impactScore: impactScore,
            confirmations: 1, // submitter auto-confirms
            rejections: 0,
            requiredQuorum: quorum,
            finalized: false,
            accepted: false,
            submitter: msg.sender,
            submittedAt: uint48(block.timestamp)
        });

        hasVoted[reportId][msg.sender] = true;

        emit ReportSubmitted(reportId, personId, msg.sender);

        // Check if single agent can finalize
        if (quorum <= 1) {
            _finalize(reportId);
        }

        return reportId;
    }

    /// @notice Vote on a pending report.
    function vote(uint256 reportId, bool approve) external onlyAgent {
        Report storage r = reports[reportId];
        if (r.finalized) revert AlreadyFinalized();
        if (hasVoted[reportId][msg.sender]) revert AlreadyVoted();

        hasVoted[reportId][msg.sender] = true;

        if (approve) {
            r.confirmations++;
        } else {
            r.rejections++;
        }

        emit VoteCast(reportId, msg.sender, approve);

        // Check quorum
        if (r.confirmations >= r.requiredQuorum) {
            _finalize(reportId);
        } else if (r.rejections > agentCount - r.requiredQuorum) {
            // Impossible to reach quorum — reject
            r.finalized = true;
            r.accepted = false;
            emit ReportFinalized(reportId, false, r.impactScore);
        }
    }

    /// @notice Get report details.
    function getReport(uint256 reportId) external view returns (Report memory) {
        return reports[reportId];
    }

    function _finalize(uint256 reportId) internal {
        Report storage r = reports[reportId];
        r.finalized = true;
        r.accepted = true;
        emit ReportFinalized(reportId, true, r.impactScore);
    }
}
