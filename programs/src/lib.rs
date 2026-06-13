use anchor_lang::prelude::*;

declare_id!(TreasuryGovernance1111111111111111111111111);

#[program]
pub mod treasury_governance {
    use super::*;

    pub fn initialize_treasury(ctx: Context<InitializeTreasury>, authority: Pubkey, name: String) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;
        treasury.authority = authority;
        treasury.name = name;
        treasury.total_value = 0;
        treasury.proposal_count = 0;
        treasury.created_at = Clock::get().unix_timestamp;
        Ok(())
    }

    pub fn create_proposal(ctx: Context<CreateProposal>, title: String, description: String, amount: u64) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;
        let proposal = &mut ctx.accounts.proposal;
        proposal.treasury = treasury.key();
        proposal.title = title;
        proposal.description = description;
        proposal.amount = amount;
        proposal.votes_for = 0;
        proposal.votes_against = 0;
        proposal.status = ProposalStatus::Active;
        proposal.created_at = Clock::get().unix_timestamp;
        proposal.creator = ctx.accounts.creator.key();
        treasury.proposal_count += 1;
        Ok(())
    }

    pub fn cast_vote(ctx: Context<CastVote>, vote: bool) -> Result<()> {
        let proposal = &mut ctx.accounts.proposal;
        require!(proposal.status == ProposalStatus::Active, ErrorCode::ProposalNotActive);
        // The voter_record PDA is initialized in this instruction (init), so a
        // second vote from the same wallet on the same proposal fails because
        // the account already exists. This prevents double-voting on-chain.
        let voter_record = &mut ctx.accounts.voter_record;
        voter_record.proposal = proposal.key();
        voter_record.voter = ctx.accounts.voter.key();
        voter_record.vote = vote;
        if vote {
            proposal.votes_for += 1;
        } else {
            proposal.votes_against += 1;
        }
        Ok(())
    }

    pub fn execute_proposal(ctx: Context<ExecuteProposal>) -> Result<()> {
        let proposal = &mut ctx.accounts.proposal;
        let treasury = &ctx.accounts.treasury;
        require!(proposal.status == ProposalStatus::Active, ErrorCode::ProposalNotActive);
        let total_votes = proposal.votes_for + proposal.votes_against;
        require!(total_votes > 0, ErrorCode::NoVotes);
        let quorum = proposal.votes_for as f64 / total_votes as f64;
        require!(quorum >= 0.6, ErrorCode::QuorumNotReached);
        proposal.status = ProposalStatus::Executed;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitializeTreasury<'info> {
    #[account(init, payer = authority, space = 200)]
    pub treasury: Account<'info, Treasury>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CreateProposal<'info> {
    #[account(mut)]
    pub treasury: Account<'info, Treasury>,
    #[account(init, payer = creator, space = 300)]
    pub proposal: Account<'info, Proposal>,
    #[account(mut)]
    pub creator: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CastVote<'info> {
    #[account(mut)]
    pub proposal: Account<'info, Proposal>,
    #[account(
        init,
        payer = voter,
        space = 8 + 32 + 32 + 1,
        seeds = [proposal.key().as_ref(), voter.key().as_ref()],
        bump
    )]
    pub voter_record: Account<'info, VoterRecord>,
    #[account(mut)]
    pub voter: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ExecuteProposal<'info> {
    #[account]
    pub treasury: Account<'info, Treasury>,
    #[account(mut)]
    pub proposal: Account<'info, Proposal>,
    pub authority: Signer<'info>,
}

#[account]
pub struct Treasury {
    pub authority: Pubkey,
    pub name: String,
    pub total_value: u64,
    pub proposal_count: u64,
    pub created_at: i64,
}

#[account]
pub struct Proposal {
    pub treasury: Pubkey,
    pub title: String,
    pub description: String,
    pub amount: u64,
    pub votes_for: u64,
    pub votes_against: u64,
    pub status: ProposalStatus,
    pub creator: Pubkey,
    pub created_at: i64,
}

#[account]
pub struct VoterRecord {
    pub proposal: Pubkey,
    pub voter: Pubkey,
    pub vote: bool,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq)]
pub enum ProposalStatus {
    Active,
    Executed,
    Failed,
}

#[error_code]
pub enum ErrorCode {
    ProposalNotActive,
    NoVotes,
    QuorumNotReached,
}
