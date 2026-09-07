// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract InvestmentVoting{
    enum Status{
        Ongoing,
        Approved,
        Rejected,
        Vetoed
    }

    address public immutable director;
    uint256 public immutable requiredVotes;

    uint256 public votesFor;
    uint256 public votesAgainst;

    Status public status;

    mapping(address => bool) public allowedVoters;
    mapping(address => bool) public hasVoted;

    event VoteCast(address indexed voter, bool approved);
    event VotingEnded(Status finalStatus);

    constructor(address[] memory voters){
        require(
            voters.length > 0 && voters.length % 2 ==1,
            "Invalid voters."
        );

        director = msg.sender;
        requiredVotes = voters.length / 2 + 1;
        status = Status.Ongoing;

        for(uint256 i = 0;i<voters.length;i++){
            address voter= voters[i];

            require(voter !=address(0), "Invalid address.");
            require(!allowedVoters[voter],"Duplicate voter.");

            allowedVoters[voter] = true;
        }
    }

    modifier votingIsActive(){
        require(status == Status.Ongoing,"Voting ended.");
        _;
    }

    modifier onlyAllowedVoter(){
        require(allowedVoters[msg.sender], "Invalid address.");
        require(!hasVoted[msg.sender],"Already voted.");
        _;
    }


    function voteFor()
        external
        votingIsActive
        onlyAllowedVoter
    {
        hasVoted[msg.sender]=true;
        votesFor++;

        emit VoteCast(msg.sender, true);

        if(votesFor >= requiredVotes){
            status = Status.Approved;
            emit VotingEnded(status);
        }
    }

    function voteAgainst()
        external
        votingIsActive
        onlyAllowedVoter
    {
        hasVoted[msg.sender] = true;
        votesAgainst++;

        emit VoteCast(msg.sender, false);

        if (votesAgainst >= requiredVotes) {
            status = Status.Rejected;
            emit VotingEnded(status);
        }
    }

    function veto()
        external
        votingIsActive
    {
        require(msg.sender == director, "Only director.");

        status = Status.Vetoed;
        emit VotingEnded(status);
    }
}

