# Architecture

This document describes the high-level architecture of the Unified P&L Analytics Platform.

## Core Components
- **Frontend**: Vanilla HTML/JS/CSS focusing on high-performance rendering, styled with a modern glassmorphic design system.
- **Backend API**: FastAPI framework serving REST APIs, structured using the Repository pattern.
- **Database**: PostgreSQL storing user data, P&L records, detected anomalies, and workflow executions.
- **AI Engine**: 
  - *Scikit-Learn (Isolation Forest)*: Synchronous anomaly detection.
  - *Google Gemini*: Asynchronous conversational copilot for anomaly explanation.

## Entity Relationship Diagram
```mermaid
erDiagram
    USERS {
        int id PK
        string username
        string email
        string hashed_password
        string role
        boolean is_active
        datetime created_at
    }
    PL_RECORDS {
        int id PK
        string upload_id
        string domain
        string period
        string line_item
        float amount
        string currency
        string cost_center
        json dynamic_data
        int uploaded_by FK
        datetime created_at
    }
    ANOMALIES {
        int id PK
        int pl_record_id FK
        float anomaly_score
        string severity
        boolean is_anomaly
        float percentile_rank
        string status
        datetime detected_at
        datetime resolved_at
        int assigned_to FK
    }
    RECOMMENDATIONS {
        int id PK
        int anomaly_id FK
        int priority
        string action_type
        string description
        string action_owner
        boolean sod_flag
        string estimated_impact
        string status
        datetime created_at
    }
    EXPLANATIONS {
        int id PK
        int anomaly_id FK
        string state_hash
        string explanation_text
        string root_cause
        string business_impact
        string model_version
        datetime generated_at
        int tokens_used
    }
    WORKFLOW_INSTANCES {
        int id PK
        string process_instance_id
        string workflow_name
        string status
        int started_by FK
        json variables
        datetime started_at
        datetime completed_at
    }

    USERS ||--o{ PL_RECORDS : "uploads"
    PL_RECORDS ||--o{ ANOMALIES : "analyzed_for"
    ANOMALIES ||--o{ RECOMMENDATIONS : "generates"
    ANOMALIES ||--o| EXPLANATIONS : "details"
    USERS ||--o{ WORKFLOW_INSTANCES : "triggers"
```

## System Flow
1. User uploads a CSV of financial records.
2. The Backend parses the file and saves raw `PL_RECORDS` to the DB.
3. The AI Engine asynchronously evaluates the batch of records for anomalies.
4. If an anomaly is found, it is persisted in the `ANOMALIES` table.
5. The UI fetches anomalies and can trigger the Copilot Explanation endpoint to receive human-readable AI analysis via Gemini.
