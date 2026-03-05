## Personal AI Employee Hackathon 0: Building Autonomous FTEs (Full-Time Equivalent) in 2026

# 🤖 AI CEO Autonomous Agent

An intelligent autonomous AI system designed to function as a digital CEO assistant.  
It monitors communications, generates executive briefings, manages social publishing, and integrates with business systems like Gmail, LinkedIn, WhatsApp, and Odoo.

---

## 🚀 Features

- 📧 Gmail monitoring & automated response workflows
- 📊 CEO Briefing generation
- 🔗 LinkedIn publishing automation
- 💬 WhatsApp integration
- 🏢 Odoo ERP integration
- 📁 Filesystem monitoring
- 🧠 Autonomous agent loop system
- 🐳 Docker support

---

## 🏗️ Project Architecture

The system is structured into modular components:

- **Core Engine** – Agent loop & decision processing
- **Connectors** – External service integrations
- **Generators** – Content and briefing generation
- **Watchers** – Monitoring systems
- **Utils** – Setup & utility scripts

---

## 📂 Folder Structure


```
hac0/
│
├── app/                          # Main application source code
│   ├── core/                     # Core AI system logic
│   │   ├── agent_loop.py
│   │   ├── action_processor.py
│   │   ├── autonomous_watcher.py
│   │   ├── perception_watcher.py
│   │   └── communication_hub.py
│   │
│   ├── connectors/               # External service integrations
│   │   ├── gmail_connector.py
│   │   ├── gmail_watcher.py
│   │   ├── linkedin_publisher.py
│   │   ├── whatsapp_connector.py
│   │   └── odoo_connector.py
│   │
│   ├── generators/               # Content & briefing generators
│   │   ├── ceo_briefing_generator.py
│   │   ├── generate_image_and_post.py
│   │   └── send_approval_email.py
│   │
│   ├── watchers/                 # File/system monitoring
│   │   └── filesystem_watcher.py
│   │
│   └── utils/                    # Utility & setup scripts
│       ├── db_setup.py
│       ├── create_test_data.py
│       ├── verify_setup.py
│       └── get_linkedin_token.py
│
├── config/                       # Configuration & secrets
│   ├── .env.example
│   ├── credentials.json
│   ├── odoo_config.json
│   └── mcp.json
│
├── data/                         # Runtime data
│   ├── logs/
│   ├── vault/
│   ├── Vault_Template/
│   └── token.pickle
│
├── docs/                         # Documentation
│   ├── CLAUDE.md
│   ├── Company_Handbook.md
│   └── Dashboard.md
│
├── scripts/                      # Automation scripts
│   ├── schedule_briefing.sh
│   ├── schedule_briefing.bat
│   └── send_test_email.py
│
├── skills/                       # AI skill modules
│
├── requirements.txt
├── requirements_linkedin.txt
├── Dockerfile
├── main.py
├── .gitignore
└── README.md
```

---


# ⚡ Tier Progression

<div align="center">

| Tier | Features |
|------|----------|
| 🥉 **Bronze** | • Vault structure<br>• Base watchers<br>• Inbox monitoring |
| 🥈 **Silver** | • Reasoning loop<br>• Human-in-the-Loop (HITL) approvals<br>• Task routing system<br>• MCP email integration |
| 🥇 **Gold** | • 5 MCP servers<br>• Full auditing system<br>• Automated CEO briefings<br>• Social media automation<br>• Odoo accounting integration |
| ⚡ **Platinum** | • Cloud + Local split architecture<br>• Claim-by-move system<br>• Git synchronization<br>• Full cloud deployment |

</div>

---

## 🧠 System Evolution Model

The HAC0 system is designed to evolve in structured capability tiers:

- Each tier builds on the previous.
- Architecture becomes more autonomous and distributed.
- Governance, auditing, and execution maturity increase progressively.
- Platinum represents enterprise-grade distributed AI operations.

---

## 🏗 Architecture Overview

```
Watchers → Agent Loop → Action Processor → Connectors → External Systems
```

---

## 📂 Project Structure

- `/app` → Main application logic
- `/config` → Environment & credentials
- `/data` → Logs, tokens, vault
- `/docs` → Documentation
- `/scripts` → Automation scripts

---

## ⚙️ Setup

```bash
pip install -r requirements.txt
pip install -r requirements_linkedin.txt
```

---

## ▶ Run

```bash
python main.py
```

---

## 🔒 Security

Add to `.gitignore`:

```
config/credentials.json
data/token.pickle
.env
```

---

## 🐳 Docker

```bash
docker build -t hac0 .
docker run hac0
```

---

## 🧠 Built As

**Modular Autonomous AI Executive System**

---



            ┌─────────────────────────────┐
            │  Email / Filesystem / Cloud │
            │           Inputs            │
            └──────────────┬──────────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │   Watchers Layer  │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │   Agent Loop      │
                 │      (Brain)      │
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │  Action Processor │
                 └─────────┬─────────┘
                           │
                           ▼
                   ┌─────────────────┐
                   │ Connectors Layer│
                   └─────────┬───────┘
                             │
        ┌──────────────┬──────────────┬──────────────┬──────────────┐
        │    Gmail     │   LinkedIn   │   WhatsApp   │     Odoo     │
        └──────────────┴──────────────┴──────────────┴──────────────┘
                             │
                             ▼
                 ┌─────────────────────┐
                 │   Vault + Logs      │
                 │       Update        │
                 └─────────┬───────────┘
                           │
                           ▼
                 ┌─────────────────────┐
                 │ CEO Briefing        │
                 │     Generator       │
                 └─────────────────────┘
```


   

   # 🙏 Acknowledgments
 - **Python 3.10+** — The brain behind HAC0, powering reasoning and decision-making  
- **Obsidian** — Intelligent vault interface for structured memory and context  
- **Google APIs** — Seamless Gmail & Calendar orchestration  
- **MCP Protocol** — The connective tissue for agent-tool collaboration  
- **Playwright** — Automated web interactions, making browsers your AI assistant

Built with ❤️ by **Nabila Bannay Khan**

### 💡 AI Inspiration

*"The best way to predict the future is to build it."*  
– AI-driven vision for autonomous systems
