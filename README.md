# SolanaCFO Treasury

**On-Chain Solana Treasury Management** with Multi-Agent Council Deliberation, built for [Superteam](https://superteam.ca) and the Solana ecosystem.

## Architecture

```
  DAO Members ──▶ Cognito ──▶ API Gateway ──▶ Treasury Management
                                         ──▶ Portfolio Analyzer
                                         ──▶ Risk Monitor
                                         ──▶ Yield Strategist
                                         ──▶ Governance Analyst
                                         ──▶ Treasury CFO
                                         ──▶ Council Deliberation (5 agents)
                                         ──▶ On-Chain Monitor (event-driven)
                                         ──▶ Governance Executor (on-chain)
                                         ──▶ Voice Briefings (Deepgram)

  5-Agent Council: Portfolio | Risk | Yield | Governance | CFO
            ▼
    Council Synthesizer ──▶ Final Recommendation

  On-Chain (Solana):
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ SOL Balances  │  │ SPL Tokens   │  │ Governance    │
  │ via RPC       │  │ via Anchor   │  │ Proposals     │
  └──────────────┘  └──────────────┘  └──────────────┘
```

## Features

- **5-Agent Council**: Portfolio Analyzer, Risk Monitor, Yield Strategist, Governance Analyst, Treasury CFO
- **Solana Integration**: RPC calls for SOL/SPL balances, token accounts, transaction history
- **Anchor Program**: On-chain treasury governance with token-weighted voting (Rust)
- **DeFi Analytics**: TVL, APY, impermanent loss, liquidation risk calculations
- **Governance Executor**: Create/execute proposals on-chain with quorum thresholds
- **Voice Briefings**: Deepgram TTS treasury status updates
- **Event-Driven Monitoring**: SQS-triggered alerts for large transfers and governance events
- **Observability**: PRISMtrace on BlockConvey for Bedrock calls across the council

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | AWS SAM, Python 3.12, Lambda |
| Blockchain | Solana (RPC), Anchor (Rust) |
| LLM | Amazon Bedrock (Claude 3.5 Sonnet) |
| Voice | Deepgram Nova-2 STT + Aura TTS |
| Auth | Amazon Cognito |
| Database | DynamoDB (6 tables) |
| On-Chain | Anchor framework, SPL Token operations |

## Deployment

```bash
# Backend
sam build && sam deploy --guided

# Anchor program (requires Solana CLI + Anchor)
cd programs && anchor build && anchor deploy --provider.cluster localnet
```

## License

MIT
