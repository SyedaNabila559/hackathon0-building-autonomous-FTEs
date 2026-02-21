## Personal AI Employee Hackathon 0: Building Autonomous FTEs (Full-Time Equivalent) in 2026

## 🤖 AI Employee Vault

Your Autonomous Digital Employee — Powered by Markdown

A transparent, file-native AI assistant system that thinks, plans, and executes — with you in control.

## 🌟 Overview

AI Employee Vault is a structured, autonomous agent system built entirely inside Obsidian using plain Markdown files.

Instead of hidden databases, background pipelines, or black-box automation, everything happens through visible file movements inside folders. Every action the AI takes is traceable, auditable, and reversible.

If a traditional AI assistant feels invisible, this one feels like a transparent digital employee working inside your file system.

## ⚡ Tier Roadmap

┌────────────────────────────────────────────┐
│ 🥉 BRONZE – Foundation Layer              │
├────────────────────────────────────────────┤
│ • Structured Vault Architecture           │
│ • File Watchers                           │
│ • Inbox Monitoring                        │
│ • Basic Task Capture                      │
└────────────────────────────────────────────┘


┌────────────────────────────────────────────┐
│ 🥈 SILVER – Operational Intelligence      │
├────────────────────────────────────────────┤
│ • Continuous Reasoning Loop               │
│ • Human-in-the-Loop (HITL) Approvals      │
│ • Smart Task Routing                      │
│ • MCP Email Integration                   │
└────────────────────────────────────────────┘


┌────────────────────────────────────────────┐
│ 🥇 GOLD – Executive Automation            │
├────────────────────────────────────────────┤
│ • 5 MCP Servers Active                    │
│ • Audit & Logging System                  │
│ • CEO Daily Brief Generator               │
│ • Social Media Automation                 │
│ • Odoo Accounting Integration             │
└────────────────────────────────────────────┘


┌────────────────────────────────────────────┐
│ ⚡ PLATINUM – Distributed Autonomy        │
├────────────────────────────────────────────┤
│ • Hybrid Cloud + Local Architecture       │
│ • Claim-by-Move Task Ownership Model      │
│ • Git-Based State Sync                    │
│ • Cloud Deployment Ready                  │
└────────────────────────────────────────────┘

## 📂 Project Structure

AI-Employee-Vault/
│
├── 📁 .claude/
│   └── skills/                     # Claude skill configurations
│
├── 📁 .obsidian/                   # Obsidian workspace settings
│
├── 📁 Vault_Template/              # Starter vault structure template
│
├── 📁 vault/
│   └── Needs_Action/               # Tasks awaiting processing
│
├── 📁 scripts/                     # Utility & helper scripts
│
├── 📁 skills/                      # AI skill modules
│
│
├── 📄 CLAUDE.md                    # Claude system instructions
├── 📄 Company_Handbook.md          # Internal operating rules
├── 📄 Dashboard.md                 # Vault control dashboard
├── 📄 README.md                    # Project documentation
│
├── 📄 mcp.json                     # MCP server configuration
├── 📄 odoo_config.json             # Odoo integration settings
│
├── 📄 requirements.txt             # Core dependencies
├── 📄 requirements_linkedin.txt    # LinkedIn module dependencies
│
├── 🐳 Dockerfile                   # Container configuration
│
├── 🚫 .gitignore
├── 🚫 .dockerignore
├── 🚫 .claudeignore
│
│
├── 🤖 Core Agent Engine
│   ├── main.py
│   ├── agent_loop.py
│   ├── autonomous_watcher.py
│   ├── perception_watcher.py
│   ├── filesystem_watcher.py
│   ├── action_processor.py
│   └── verify_setup.py
│
├── 📬 Communication Layer
│   ├── communication_hub.py
│   ├── gmail_connector.py
│   ├── gmail_watcher.py
│   ├── whatsapp_connector.py
│   ├── send_approval_email.py
│   └── send_test_email.py
│
├── 📢 Social & Publishing
│   ├── linkedin_publisher.py
│   ├── get_linkedin_token.py
│   └── generate_image_and_post.py
│
├── 📊 Executive Intelligence
│   ├── ceo_briefing_generator.py
│   └── schedule_briefing.sh
│   └── schedule_briefing.bat
│
├── 🏢 Business Integrations
│   ├── odoo_connector.py
│   └── db_setup.py
│
└── 🧪 Testing & Utilities
    └── create_test_data.py

   ##  🚀 Getting Started
1️⃣ Clone the Repository
git clone https:https://github.com/SyedaNabila559/hackathon0-building-autonomous-FTEs.git
cd AI-Employee-Vault
2️⃣ Create Virtual Environment (Recommended)
python -m venv venv

Activate environment:

Windows

venv\Scripts\activate

Mac / Linux

source venv/bin/activate
3️⃣ Install Dependencies
pip install -r requirements.txt

For LinkedIn module:

pip install -r requirements_linkedin.txt

*4️⃣ Configure Environment

Update mcp.json

Configure odoo_config.json

Set up Gmail API credentials

Verify connectors

Customize your Vault structure if needed

5️⃣ Verify Setup
python verify_setup.py
6️⃣ Run the AI Employee
python main.py

Your autonomous file-driven AI system is now live.

🐳 Run with Docker (Optional)

Build:

docker build -t ai-employee-vault .

Run:

docker run -d ai-employee-vault**

## 🙏 Acknowledgments

AI Employee Vault stands on the shoulders of powerful open-source tools and ecosystems that make transparent autonomy possible.

This system is built with:

Python 3.10+ — The core engine powering automation, orchestration, and reasoning logic

Obsidian — The human-readable vault interface where every state lives as Markdown

Google APIs — Secure integration for Gmail and Calendar workflows

MCP Protocol — Modular agent-to-tool communication architecture

Playwright — Reliable browser automation for web-based execution

Each of these technologies plays a critical role in ensuring that the AI remains:

Transparent

Extensible

Auditable

Human-controlled

  Built with ❤️ by Nabila Bannay Khan
  
  “The best AI isn’t the one that hides in the cloud.
It’s the one that works beside you — in folders you control.”

— AI Employee Vault
