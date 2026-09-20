# CANONICAL AGENT & SUBSYSTEM REGISTRY

**Unified P&L Intelligence Platform**  
**Architecture Classification & Inventory**  
**Status:** Runtime-Verified & Operational  

---

## 1. Single Source of Truth for Agent Architecture

To resolve historical discrepancies across early project proposals and runtime implementations, this document establishes the **canonical taxonomy** of the platform's multi-agent architecture:

$$\text{Total Agentic Ecosystem} = \mathbf{6\text{ Autonomous \& Specialist Agents}} + \mathbf{4\text{ Supporting Agentic Components}} + \mathbf{1\text{ Workflow Orchestrator}}$$

### High-Level Architectural Diagram
```mermaid
graph TD
    User([Financial Analyst / Controller]) -->|Natural Language Goal| Orchestrator[Financial Orchestrator Agent (ReAct)]
    User -->|File Ingestion Pipeline| Camunda[Camunda BPMN Orchestrator]
    
    subgraph Autonomous_and_Specialist_Agents [Autonomous & Specialist Agents]
        Orchestrator -->|1. Goal Decomposition & Planning| Orchestrator
        Orchestrator -->|2. Dynamic Tool Calling| ToolsRegistry[Controlled Agent Tools Registry]
        Orchestrator -->|3. Mathematical & Semantic Guardrail| ValidationAgent[Financial Validation Agent]
        Orchestrator -->|4. Non-Destructive Stress Testing| ScenarioAgent[Scenario / What-If Agent]
        ToolsRegistry --> DataQualityAgent[Data Quality Agent]
        ToolsRegistry --> SchemaMappingAgent[Schema Mapping Agent]
        Orchestrator --> LearningAgent[Learning Agent (Adaptive Weights)]
    end
    
    subgraph Supporting_Agentic_Components [Supporting Agentic Components]
        Orchestrator --> AgentMemory[Agent Memory Subsystem]
        ToolsRegistry --> ForecastEngine[Forecast Agent / ML Regressor]
        ToolsRegistry --> ExplanationAgent[Explanation Component (LLM Specialist)]
        SystemSurveillance[Monitoring Agent] --> TelemetryDB[(AILog Database)]
    end
    
    subgraph Camunda_BPMN_Engine [Camunda BPMN Workflow Engine]
        Camunda --> Worker1[Worker: upload_data]
        Worker1 --> Worker2[Worker: validate_data]
        Worker2 --> Worker3[Worker: process_pl]
        Worker3 --> Worker4[Worker: anomaly_detection]
        Worker4 --> Worker5[Worker: forecast]
        Worker5 --> Worker6[Worker: risk_assessment]
        Worker6 --> Gateway{Approval Required?}
        Gateway -->|High Risk| HITL[User Task: Controller Approval (PAUSES)]
        HITL -->|Approved| Worker7[Worker: generate_report]
        HITL -->|Rejected| EndFailed[End: Analysis Rejected]
        Worker7 --> EndCompleted[End: Workflow Completed]
    end
```

---

## 2. Inventory of Autonomous & Specialist Agents (6 Agents)

### 1. Financial Orchestrator Agent
- **File:** [`backend/agents/financial_orchestrator_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/agents/financial_orchestrator_agent.py)
- **Role:** Master Autonomous Reasoning Agent (ReAct Loop).
- **Autonomy:** **Autonomous**. Independently parses natural language goals, deconstructs multi-part intents, formulates multi-step plans, selects and executes registry tools, correlates findings, passes candidate answers to guardrails, and outputs structured execution traces.
- **Input:** Natural language financial queries (e.g. *"Which department is most profitable and which is 2nd least profitable?"*).
- **Output:** Structured `ExecutionTrace` containing planned steps, executed tool records, validation outcome, and executive answer.
- **Tools Used:** `get_kpis`, `get_department_analysis`, `compare_periods`, `run_what_if_tool`, `detect_anomalies_tool`, `generate_recommendations_tool`, `run_forecast`, `get_memory_feedback`.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 2. Financial Validation Agent
- **File:** [`backend/agents/validation_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/agents/validation_agent.py)
- **Role:** Autonomous Mathematical & Semantic Guardrail.
- **Autonomy:** **Specialist Guardrail**. Intercepts candidate statements before emission, validates accounting equations ($Rev - Exp = Profit$), operating margin formulas, ordinal rankings against database ground truth, and automatically replaces erroneous candidates with verified data.
- **Input:** Claimed KPI totals, candidate response text, and decomposed intents.
- **Output:** `ValidationResult` (Boolean `is_valid`, confidence score, discrepancy logs, and `corrected_payload`).
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 3. Scenario Agent (What-If Analysis)
- **File:** [`backend/agents/scenario_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/agents/scenario_agent.py)
- **Role:** Specialist Financial Stress-Testing Agent.
- **Autonomy:** **Specialist Agent**. Executes deterministic non-destructive multi-variable financial simulations (revenue growth, OPEX changes, department cost reductions), computes profit and margin deltas, and determines risk classifications.
- **Input:** Baseline financials, revenue growth percentage, expense adjustment percentage.
- **Output:** Simulation matrix containing baseline metrics, modeled metrics, profit delta, margin shift, and strategic advice.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 4. Learning Agent
- **File:** [`backend/services/learning_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/services/learning_agent.py)
- **Role:** Autonomous Adaptive Learning & Feedback Processing.
- **Autonomy:** **Autonomous**. Intercepts executive approvals, rejections, and direct feedback on recommendations; dynamically adjusts domain ranking weights; and persists preference rules.
- **Input:** Recommendation decision payload (`ACCEPT`, `REJECT`), feedback notes, affected department domain.
- **Output:** Updated domain weightings and memory confirmation.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 5. Data Quality Agent
- **File:** [`backend/services/data_quality_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/services/data_quality_agent.py)
- **Role:** Specialist Ingestion Hygiene & Anomaly Screening.
- **Autonomy:** **Specialist Agent**. Evaluates raw uploaded spreadsheets, detects missing cells, validates date continuity, and checks Segregation of Duties (SoD) compliance.
- **Input:** Raw dataset upload payload.
- **Output:** Data quality scorecard and hygiene flags.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 6. Schema Mapping Agent
- **File:** [`backend/services/schema_mapping_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/services/schema_mapping_agent.py)
- **Role:** Specialist Semantic Ingestion & Column Alignment Agent.
- **Autonomy:** **Specialist Agent**. Analyzes arbitrary spreadsheet headers and matches them to standard P&L schema dimensions (Period, Domain, Line Item, Amount, Revenue, Expense) using fuzzy and semantic similarity.
- **Input:** Raw spreadsheet column headers and sample rows.
- **Output:** Standardized column mapping dictionary with confidence scores.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

---

## 3. Supporting Agentic & Analytical Components (4 Components)

### 7. Agent Memory Subsystem
- **File:** [`backend/agents/memory_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/agents/memory_agent.py)
- **Classification:** **Memory / Context Subsystem**.
- **Role:** Persists human manager decisions, directives, and rejections in the SQLite `settings` table and retrieves context during subsequent reasoning turns.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 8. Explanation Agent
- **File:** [`backend/services/explanation_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/services/explanation_agent.py)
- **Classification:** **LLM-Based Explanation Specialist Component**.
- **Role:** Generates structured root cause analyses for flagged outliers and caches outputs by deterministic SHA-256 state hash.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 9. Forecast Agent (Predictive Engine)
- **File:** [`backend/services/forecast_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/services/forecast_agent.py)
- **Classification:** **Predictive ML Analytics Component**.
- **Role:** Fits OLS Linear Regression over historical periods to generate upcoming 3–12 month baseline forecasts with $R^2$ statistical goodness-of-fit.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

### 10. Monitoring Agent
- **File:** [`backend/services/monitoring_agent.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/services/monitoring_agent.py)
- **Classification:** **Surveillance & Risk Telemetry Component**.
- **Role:** Continuously inspects active financial health, outlier volume, margin degradation, and logs audit alerts.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

---

## 4. Workflow Orchestration Engine (1 System)

### 11. Camunda BPMN Workflow Engine & External Workers
- **Files:**
  - BPMN Definition: [`backend/camunda/pl_financial_workflow.bpmn`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/camunda/pl_financial_workflow.bpmn)
  - REST Client: [`backend/camunda/client.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/camunda/client.py)
  - Worker Daemon: [`backend/camunda/workers.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/camunda/workers.py)
  - State Machine: [`backend/services/workflow_service.py`](file:///c:/Users/HP/.gemini/antigravity-ide/scratch/P&L%20system/unified-pl-system/backend/services/workflow_service.py)
- **Process Definition Key:** `Process_PLFinancialOrchestration`
- **Workflow Topics (7):** `upload_data`, `validate_data`, `process_pl`, `anomaly_detection`, `forecast`, `risk_assessment`, `generate_report`.
- **Human-in-the-Loop:** Pauses at `User Task` (`manager_approval`) and transitions to `COMPLETED` on approval or `FAILED` on rejection.
- **Dual-Mode Execution:** Auto-connects to standalone Camunda REST API (`localhost:8080/engine-rest`) when live, or executes the Integrated Enterprise BPMN State Machine when offline.
- **Runtime Status:** **VERIFIED WORKING (PASS)**.

---

## 5. Summary Matrix

| Component Name | File | Primary Responsibility | Classification | Autonomy Status | Live Verified? |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Financial Orchestrator** | `financial_orchestrator_agent.py` | Goal parsing, planning, tool dispatching, synthesis | Core Agent | **Autonomous** | **YES (PASS)** |
| **Financial Validation Agent** | `validation_agent.py` | Accounting identity ($Rev - Exp = Profit$) & semantic checks | Guardrail Agent | **Specialist Guardrail** | **YES (PASS)** |
| **Scenario Agent** | `scenario_agent.py` | Non-destructive What-If stress testing | Specialist Agent | **Specialist Agent** | **YES (PASS)** |
| **Learning Agent** | `learning_agent.py` | Adaptive domain weight adjustment from human feedback | Adaptive Agent | **Autonomous** | **YES (PASS)** |
| **Data Quality Agent** | `data_quality_agent.py` | Missing data & SoD compliance checks | Specialist Agent | **Specialist Agent** | **YES (PASS)** |
| **Schema Mapping Agent** | `schema_mapping_agent.py` | Automated spreadsheet column alignment | Specialist Agent | **Specialist Agent** | **YES (PASS)** |
| **Agent Memory** | `memory_agent.py` | Decision & rejection persistence across sessions | Subsystem | Context Component | **YES (PASS)** |
| **Explanation Agent** | `explanation_agent.py` | Anomaly root cause explanation generation | Component | LLM Specialist | **YES (PASS)** |
| **Forecast Engine** | `forecast_agent.py` | Time-series regression forecasting | ML Component | Analytics Tool | **YES (PASS)** |
| **Monitoring Agent** | `monitoring_agent.py` | Margin degradation & outlier surveillance | Component | Telemetry Tool | **YES (PASS)** |
| **Camunda BPMN Orchestrator** | `workflow_service.py` | 8-stage BPMN lifecycle & HITL approval | Workflow Engine | Orchestrator | **YES (PASS)** |
