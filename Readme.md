🌿 VrukshaChain – Blockchain-based Ayurvedic Herb Traceability System
📌 Overview

VrukshaChain is a blockchain-based traceability platform for Ayurvedic herbs, ensuring authenticity, quality, and sustainable sourcing.
This proof-of-concept integrates AI-powered validation agents to verify collection events against geo-tagged data, regulatory norms, and quality standards, with a Streamlit-based UI for interaction.

✨ Key Features
🔗 Blockchain Traceability

Immutable ledger of collection → processing → testing → formulation.

Smart contracts for geo-fencing, seasonal restrictions, and quality checks.

🤖 AI Validation Agents

Groq-powered LLM for compliance analysis and recommendations.

Serper API integration for fetching regulatory updates in real time.

Modular agents: satellite, regulatory, quality.

📍 Geo-tagged Collection

GPS validation of harvest locations.

Folium maps for visualization.

Conservation status and harvesting season checks.

🧪 Quality Compliance

Validates moisture, ash content, contamination presence.

Generates compliance reports with confidence scores.

📊 Streamlit Dashboard

Collection Validation – Validate events manually / via JSON / sample data.

Sample Data Explorer – Explore and analyze events with charts.

System Health – Monitor orchestrator, agents, and services.

About – System configuration, supported species, and quality standards.

🏗️ Project Structure
VrukshaChain AI validation agent/
│── agents/              # LLM + Orchestrator agents
│── config/              # Settings and configuration
│── core/                # Core validation (satellite, regulatory, quality)
│── data/                # Sample datasets
│── deployments/         # Deployment adapters (MCP-ready)
│── logs/                # Application logs
│── models/              # Pydantic models & schemas
│── notebooks/           # Experiments & analysis
│── tests/               # Unit tests
│── utils/               # Helpers and utilities
│── main.py              # Streamlit application entry point
│── requirements.txt     # Dependencies
│── .env.template        # Env variables template
│── README.md            # Documentation

⚙️ Installation & Setup
🔧 1. Clone the repository
git clone https://github.com/HaRsH00000007/Sih.git
cd Sih

🔧 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows

🔧 3. Install dependencies
pip install -r requirements.txt

🔧 4. Setup environment variables

Create a .env file (use .env.template as reference):

GROQ_API_KEY=your_groq_api_key
SERPER_API_KEY=your_serper_api_key


⚠️ Do not commit .env to GitHub (already in .gitignore).

🔧 5. Run the Streamlit app
streamlit run main.py

📷 Screenshots
🔍 Collection Validation

Validates events with geo-tag, regulatory, and quality checks.

📊 Analytics Dashboard

Explore species distribution, conservation status, and quality metrics.

⚡ System Health

Monitor orchestrator and AI agents in real time.

📡 APIs & Integrations

Groq LLM API – AI compliance analysis.

Serper API – Regulatory updates (free 2,500 searches).

Folium & Plotly – Geospatial maps and analytics.

Hyperledger Fabric (planned) – Blockchain traceability ledger.

🧪 Demo Workflow

Collector records a geo-tagged event.

AI agents validate location, season, and conservation rules.

Quality metrics checked against pharmacopeial standards.

Results displayed in Streamlit dashboard with compliance score.

QR code (planned) for end-to-end provenance traceability.

🚀 Roadmap

 Full blockchain integration with Hyperledger Fabric.

 Consumer-facing QR code provenance explorer.

 IoT-based field data collection.

 MCP deployment for multi-agent collaboration.

👨‍💻 Contributors

Harsh Singh – Developer, AI Agent Architect

Mentorship: Ministry of Ayush – AIIA

📜 License

This project is licensed under the MIT License.
