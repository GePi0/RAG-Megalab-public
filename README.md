
	# 🤖 RAG‑MEGALAB  
	### _Cognitive Full‑Stack → Retrieval‑Augmented Generation + Autonomous DevOps Intelligence_
	
	---
	
	## 🧠 Overview
	
	**RAG‑Megalab** is a modular AI laboratory that fuses  
	**Retrieval‑Augmented Generation**, **multi‑agent reasoning**, and  
	**self‑healing DevOps automation** into a single cohesive system.
	
	It behaves as a **Cognitive Developer Agent**:  
	an AI entity capable of reasoning, coding, evaluating, repairing, and learning  
	from every cycle — a real foundation for auditable and autonomous AI operations.
	
	---
	
	## ⚙️ Core Architecture
	
	| Layer | Purpose | Major Components |
	|-------|----------|------------------|
	| **API / Gateway** | Entry point and user interface for prompts | FastAPI + Uvicorn |
	| **Orchestrator (Llama 3.1)** | Main reasoning brain + cognitive pipeline | Strategy Manager, Policy Manager, Healing Manager |
	| **Workers MCP (Code Llama 7B)** | Code generation and task execution engine | Async delegation via HTTP |
	| **Context Service (Chroma DB)** | Vectorized context memory and persistence | retrieval / embedding store |
	| **State Manager** | Cognitive event bus (Kafka → Elastic + Grafana) | observability + feedback |
	| **Health & Healing System (14‑A / B)** | Real‑time monitoring, auto‑repair, and semantic healing | Docker SDK + elastic trace |
	| **File I/O & Snapshots (11‑bis)** | Versioned artifact writer with undo/redo | Manifest + Snapshot Manager |
	| **Context Awareness (12)** | Filesystem perception & dependency analysis | Context Observer |
	| **Scheduler Multi‑Agent (13)** | Parallel reasoning & consensus across agents | Async Scheduler |
	| **LangGraph Pipelines (15)** | CI/CD orchestration for autonomous workflows | future integration |
	
	---
	
	## 🧩 Cognitive Workflow

Prompt

↓

Reason (Orchestrator  Llama 3.1)

↓

Act (Workers MCP — Code Llama 7B)

↓

Write (File Writer → workdir)

↓

Snapshot & Version (ZIP + Manifest)

↓

Observe → Context Awareness → Meta‑Reflection

↓

Heal → Feedback → Learn → Adjust


	The cycle _observe → reason → act → evaluate → learn → self‑adjust_  
	turns every execution into an auditable feedback‑driven learning process.
	
	---
	
	## 🧱 Tech Stack
	
	**Languages & Frameworks**
	- Python 3.11 / FastAPI / LangChain / AsyncIO  
	- Kafka + Redpanda / ElasticSearch / Grafana / Chroma DB  
	- Docker & Docker‑Compose multi‑service architecture  
	- Llama 3.1 (Reasoner) + Code Llama 7B (Executor)  
	- YAML / JSON structured feedback and weights management  
	
	**Conceptual pillars**
	- Retrieval‑Augmented Generation (RAG)
	- Meta Reflexion & Adaptive Policies
	- DevOps Self‑Healing via Docker SDK
	- Cognitive Feedback Loops (+/‑ reinforcement ≈ RLHF safe)
	
	---
	
	## 🔁 Current Capabilities
	
	- ✅ **Autonomous code generation & execution**  
	- ✅ **Real‑time health monitoring** + intelligent auto‑repair  
	- ✅ **Semantic healing** based on LLM meta‑reasoning  
	- ✅ **Versioned artifact management (undo/redo)**  
	- ✅ **Parallel multi‑agent scheduling & consensus**  
	- ✅ **Dynamic policy weights adapting per success rate**  
	- ✅ **Full observability (AI telemetry → Elastic/Grafana)**  
	
	---
	
	## 🚀 Roadmap (in progress)
	
	| Phase | Focus |
	|-------|-------|
	| **14 B** | Healing Manager completed → semantic auto‑repair |
	| **12 / 12 bis** | Context Awareness + Observation Rules ✓ |
	| **11 bis** | Intelligent FileWriter + Snapshooter ✓ |
	| **13** | Multi‑Agent Scheduler ✓ |
	| **15** | LangGraph Pipelines (CI/CD graph execution) 🔜 |
	| **16** | Docs / Testing / Open API Publication 🔜 |
	
	---
	
	## 🧰 Deployment (dev mode)
	
	```bash
	git clone https://github.com/<yourname>/rag-megalab.git
	cd rag-megalab
	docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d --build

All services run under the internal network megalab_net.

Default ports: API (8000) | Orchestrator (8001) | Context (8002) | Worker (8003) | Elastic (9200) | Grafana (3000).


---

🧩 Folder Structure (overview)

	rag‑megalab/
	├── api/
	├── orchestrator/
	│   ├── file_writer.py
	│   ├── healing_manager.py
	│   ├── health_manager.py
	│   ├── scheduler_multiagent.py
	│   ├── policy_manager.py
	│   └── project_manager/
	│        ├── manifest.py
	│        └── snapshot_manager.py
	├── worker_mcp/
	├── context_service/
	├── state_manager/
	├── storage/
	└── docker-compose*.yml


---

🧩 Author


Gerard Piella Olmedo [AI Engineer & DevOps Projects]

Backend Automation • Cognitive Systems • LLM Ops • Infrastructure as Reasoning


Designed for research, traceability and auditable automation —

a demonstration of how cognitive DevOps and adaptive RAG systems can coexist in production‑grade environments.



---

	📜 License
	This repository provides research‑level source code for educational
	and non‑commercial demonstration purposes.
	All trademarks and model names belong to their respective owners.
