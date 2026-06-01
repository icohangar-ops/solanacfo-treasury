# 🔐 SolanaCFO Treasury

> **On-Chain Solana Treasury Management Platform with Multi-Agent Council Deliberation**
>
> Built for the Solana ecosystem via [Superteam](https://superteam.ca)

[![Superteam Hackathon](https://img.shields.io/badge/Superteam-Hackathon-9945FF?logo=solana&logoColor=white)](https://superteam.ca)
[![AWS SAM](https://img.shields.io/badge/AWS-SAM_Serverless-FF9900?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/serverless/sam/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Solana](https://img.shields.io/badge/Solana-Mainnet_Beta-9945FF?logo=solana&logoColor=white)](https://solana.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SolanaCFO Treasury                              │
│                    Multi-Agent Council Deliberation                     │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │   Solana     │     │   Amazon     │     │   Frontend   │
  │   RPC / WSS  │     │   Cognito    │     │   (dApp)     │
  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
         │                    │                     │
         ▼                    ▼                     ▼
  ┌──────────────────────────────────────────────────────────┐
  │                    API Gateway (REST)                     │
  └──────────────────────────┬───────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
  │  Treasury    │   │  Council     │   │  On-Chain        │
  │  Management  │   │  Deliberation│   │  Monitor         │
  │  Lambda      │   │  Lambda      │   │  Lambda          │
  └──────┬──────┘   └──────┬──────┘   └────────┬─────────┘
         │                 │                    │
         ▼                 ▼                    ▼
  ┌──────────────────────────────────────────────────────────┐
  │              Council of 5 AI Agents                       │
  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ ┌─────┐ │
  │  │Portfolio│ │  Risk   │ │  Yield  │ │Govern. │ │CFO  │ │
  │  │Analyzer │ │ Monitor │ │Strategist│ │Analyst│ │Agent│ │
  │  └─────────┘ └─────────┘ └─────────┘ └────────┘ └─────┘ │
  └──────────────────────┬───────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  ┌────────────┐  ┌────────────┐  ┌───────────────┐
  │  Bedrock   │  │  DynamoDB  │  │   Solana      │
  │  Claude 3.5│  │  6 Tables  │  │   RPC + SPL   │
  │  Sonnet    │  │            │  │   Token Ops   │
  └────────────┘  └────────────┘  └───────────────┘
         │               │               │
         ▼               ▼               ▼
  ┌────────────┐  ┌────────────┐  ┌───────────────┐
  │   SNS /    │  │    S3      │  │  Anchor       │
  │   SQS      │  │  Reports & │  │  Governance   │
  │   Alerts   │  │  Audio     │  │  Program      │
  └────────────┘  └────────────┘  └───────────────┘
```

## Features

### 🏦 Treasury Management
- Create and manage on-chain treasuries linked to Solana wallets
- Multi-sig governance with SPL token-weighted voting
- Automatic asset allocation tracking across DeFi protocols
- Real-time balance and position monitoring via Solana RPC

### 🤖 Multi-Agent Council Deliberation
- **Portfolio Analyzer** — Analyzes on-chain positions, DEX exposure, LP positions
- **Risk Monitor** — Monitors price exposure, liquidation risk, smart contract risk
- **Yield Strategist** — Identifies yield opportunities across Solana DeFi
- **Governance Analyst** — Analyzes DAO proposals, token voting patterns
- **Treasury CFO** — Overall treasury health, cash flow, rebalancing recommendations
- **Council Synthesizer** — Produces final risk-adjusted recommendations

### 📊 DeFi Analytics
- Total Value Locked (TVL) tracking across protocols
- APY/APR comparison and optimization
- Impermanent loss calculation for LP positions
- Liquidation risk scoring and alerts

### 🔔 On-Chain Monitoring
- Real-time Solana account change subscriptions via WebSocket
- Large transfer detection (>5% of treasury)
- Liquidation event monitoring
- Governance vote tracking
- Price and risk alerts via SNS

### 🎙️ Voice Briefings
- Deepgram Nova-2 Speech-to-Text for voice commands
- Deepgram Aura Text-to-Speech for treasury briefings
- Automated daily/weekly audio reports

### 🔒 Security
- Custom VPC with 3 availability zones
- KMS Customer Managed Keys for encryption
- Amazon Cognito with Solana wallet login
- Least-privilege IAM roles
- CloudWatch monitoring and alarms

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | AWS SAM (Serverless Application Model) |
| Runtime | Python 3.12 Lambda |
| LLM Orchestration | Amazon Bedrock (Claude 3.5 Sonnet) |
| Blockchain | Solana Web3.py (solana-py) + Anchor |
| Token Operations | SPL Token (anchorpy) |
| Voice STT/TTS | Deepgram Nova-2 / Aura |
| Authentication | Amazon Cognito |
| Database | DynamoDB (6 tables) |
| Storage | S3 (reports, audio, docs) |
| Messaging | SQS (async monitoring) + SNS (alerts) |
| On-Chain Program | Anchor (Rust) |

## Quick Start

### Prerequisites

```bash
# Install AWS SAM CLI
pip install aws-sam-cli

# Install Python dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure

# Set Solana RPC endpoint
export SOLANA_RPC_URL="https://api.mainnet-beta.solana.com"
export SOLANA_WSS_URL="wss://api.mainnet-beta.solana.com"
```

### Deploy

```bash
# Build the application
sam build

# Deploy to AWS (guided)
sam deploy --guided

# Deploy with saved config
sam deploy --config-file samconfig.toml
```

### Local Development

```bash
# Start local API
sam local start-api

# Invoke a Lambda locally
sam local invoke TreasuryManagementFunction -e events/treasury_create.json

# Run tests
python -m pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/treasury/create` | Create a new treasury |
| `GET` | `/treasury/{id}` | Get treasury details |
| `PUT` | `/treasury/{id}` | Update treasury parameters |
| `GET` | `/portfolio/{treasury_id}` | Analyze portfolio positions |
| `GET` | `/risk/{treasury_id}` | Get risk assessment |
| `GET` | `/yield/opportunities` | List yield opportunities |
| `POST` | `/council/deliberate` | Start council deliberation |
| `GET` | `/council/{deliberation_id}` | Get deliberation results |
| `POST` | `/governance/propose` | Create governance proposal |
| `POST` | `/governance/vote` | Cast vote on proposal |
| `POST` | `/voice/briefing` | Generate voice briefing |

## Anchor Program

The on-chain governance program is located in `programs/`. Build and deploy:

```bash
cd programs
anchor build
anchor deploy --provider.cluster mainnet-beta
```

### Program Instructions

- `initialize_treasury` — Create treasury PDA account
- `create_proposal` — Submit governance proposal (requires governance tokens)
- `cast_vote` — Vote on active proposal (weighted by token holdings)
- `execute_proposal` — Execute passed proposal (quorum + majority threshold)
- `disburse_funds` — Transfer funds from treasury per executed proposal

## Project Structure

```
solanacfo-treasury/
├── template.yaml              # AWS SAM template
├── infrastructure/            # Nested CloudFormation stacks
├── lambdas/                   # Lambda function source code
│   ├── common/                # Shared utilities
│   └── */                     # Individual Lambda handlers
├── agents/                    # AI Agent implementations
├── prompts/                   # System prompts for agents
├── programs/                  # Anchor on-chain program
├── tests/                     # Test suites
└── docs/                      # Documentation
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SOLANA_RPC_URL` | Solana RPC endpoint | Yes |
| `SOLANA_WSS_URL` | Solana WebSocket endpoint | Yes |
| `DEEPGRAM_API_KEY` | Deepgram API key | Yes |
| `BEDROCK_REGION` | Bedrock region | Yes |
| `COGNITO_USER_POOL_ID` | Cognito User Pool | Yes |

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for [Superteam](https://superteam.ca)
- Powered by [Solana](https://solana.com) and [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- AI Agents orchestrated via Claude 3.5 Sonnet
