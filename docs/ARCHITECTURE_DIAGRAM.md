# FBP Architecture Diagram

This document contains Mermaid diagrams visualizing the FBP project structure and data flow.

## System Overview

```mermaid
graph TB
    subgraph "External Tools & Clients"
        n8n[n8n Workflows]
        LM[LM Studio Agents]
        Scripts[Custom Scripts/Bots]
        Other[Other Automation Tools]
    end

    subgraph "FBP - FastAPI Backend"
        subgraph "Routers Layer"
            Health[health.py<br/>GET /health]
            Echo[echo.py<br/>POST /echo]
            NFA_Mock[nfa.py<br/>POST /nfa/test]
            NFA_Real[nfa_real.py<br/>POST /nfa/create<br/>GET /nfa/status]
            REDESIM[redesim.py<br/>POST /redesim/email-extract<br/>GET /redesim/status]
        end

        subgraph "Services Layer"
            EchoSvc[echo_service.py]
            NFASvc[nfa_service.py<br/>Mock]
            NFARealSvc[nfa_real_service.py<br/>Real Automation]
            REDESIMSvc[redesim_service.py]
        end

        subgraph "Core Layer"
            Jobs[jobs.py<br/>Job Tracking System]
            Clients[clients.py<br/>HTTP/Internal Clients]
            Config[config.py<br/>Settings]
            Logger[logger.py<br/>Logging]
            Exceptions[exceptions.py<br/>Error Handling]
        end

        subgraph "Utils"
            Helpers[helpers.py]
        end
    end

    subgraph "External Automation Services"
        NFA_Service[NFA Automation Service<br/>HTTP or Local]
        REDESIM_Service[REDESIM Automation Service<br/>HTTP or Local]
    end

    %% External connections
    n8n --> Health
    n8n --> Echo
    n8n --> NFA_Real
    n8n --> REDESIM
    LM --> NFA_Real
    LM --> REDESIM
    Scripts --> Health
    Scripts --> NFA_Real
    Other --> Health

    %% Router to Service connections
    Health --> EchoSvc
    Echo --> EchoSvc
    NFA_Mock --> NFASvc
    NFA_Real --> NFARealSvc
    REDESIM --> REDESIMSvc

    %% Service to Core connections
    NFARealSvc --> Jobs
    NFARealSvc --> Clients
    REDESIMSvc --> Jobs
    REDESIMSvc --> Clients
    EchoSvc --> Logger
    NFASvc --> Logger

    %% Core to External Services
    Clients --> NFA_Service
    Clients --> REDESIM_Service

    %% Core internal connections
    Jobs --> Logger
    Clients --> Config
    NFARealSvc --> Config
    REDESIMSvc --> Config

    %% Styling
    classDef router fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef service fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef core fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef external fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px

    class Health,Echo,NFA_Mock,NFA_Real,REDESIM router
    class EchoSvc,NFASvc,NFARealSvc,REDESIMSvc service
    class Jobs,Clients,Config,Logger,Exceptions core
    class n8n,LM,Scripts,Other,NFA_Service,REDESIM_Service external
```

## Request Flow - Phase 1 (Simple Endpoints)

```mermaid
sequenceDiagram
    participant Client as External Tool/Client
    participant Router as Router Layer
    participant Service as Service Layer
    participant Core as Core (Logger/Config)

    Client->>Router: HTTP Request (e.g., POST /echo)
    Router->>Router: Validate Input
    Router->>Service: Call service function
    Service->>Core: Log activity
    Service->>Service: Process request
    Service->>Router: Return result
    Router->>Client: HTTP Response
```

## Request Flow - Phase 2 (Job-Based Automation)

```mermaid
sequenceDiagram
    participant Client as External Tool/Client
    participant Router as Router (nfa_real/redesim)
    participant Service as Service Layer
    participant Jobs as Job System
    participant Automation as External Automation Service

    Client->>Router: POST /nfa/create (with data)
    Router->>Router: Validate Input
    Router->>Service: create_nfa_job(payload)
    Service->>Jobs: Create job (get job_id)
    Service->>Service: Dispatch background task
    Service->>Router: Return {job_id, status: "queued"}
    Router->>Client: HTTP 200 Response (job_id)

    Note over Service,Automation: Background execution starts
    Service->>Jobs: Update job status to "running"
    Service->>Automation: Execute automation (HTTP or local)
    Automation-->>Service: Return result
    Service->>Jobs: Update job status to "completed" + result

    Client->>Router: GET /nfa/status/{job_id}
    Router->>Service: get_nfa_job_status(job_id)
    Service->>Jobs: Get job by ID
    Jobs-->>Service: Return job data
    Service->>Router: Return job status + result
    Router->>Client: HTTP 200 Response (status, result)
```

## Job Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Queued: Job Created
    Queued --> Running: Background task starts
    Running --> Completed: Success
    Running --> Failed: Error occurred
    Running --> Timeout: Time limit exceeded
    Completed --> [*]: Job finished
    Failed --> [*]: Job finished
    Timeout --> [*]: Job finished

    note right of Queued
        Job created with unique ID
        Client receives job_id immediately
    end note

    note right of Running
        Automation service executing
        Can take seconds to minutes
    end note

    note right of Completed
        Result stored in job
        Client can retrieve result
    end note
```

## Component Relationships

```mermaid
graph LR
    subgraph "Phase 1 - Simple"
        A1[Router] --> B1[Service]
        B1 --> C1[Response]
    end

    subgraph "Phase 2 - Job-Based"
        A2[Router] --> B2[Service]
        B2 --> C2[Job System]
        C2 --> D2[Background Task]
        D2 --> E2[Automation Client]
        E2 --> F2[External Service]
        F2 --> E2
        E2 --> C2
        C2 --> B2
        B2 --> A2
    end

    style A1 fill:#e1f5ff
    style A2 fill:#e1f5ff
    style B1 fill:#f3e5f5
    style B2 fill:#f3e5f5
    style C2 fill:#fff3e0
    style E2 fill:#fff3e0
```

## Integration Modes

```mermaid
graph TB
    subgraph "FBP Backend"
        Service[Service Layer]
        ClientFactory[Client Factory]
    end

    subgraph "HTTP Mode"
        HTTPClient[HTTP Client]
        HTTPService[External HTTP Service<br/>Running separately]
    end

    subgraph "Local Mode"
        LocalClient[Local Library Client]
        LocalCode[Python Code<br/>Same process]
    end

    Service --> ClientFactory
    ClientFactory -->|Mode: http| HTTPClient
    ClientFactory -->|Mode: local| LocalClient
    HTTPClient --> HTTPService
    LocalClient --> LocalCode

    style Service fill:#f3e5f5
    style ClientFactory fill:#fff3e0
    style HTTPClient fill:#e8f5e9
    style LocalClient fill:#e8f5e9
```

## Error Handling Flow

```mermaid
graph TD
    Request[HTTP Request] --> Validate{Validation}
    Validate -->|Invalid| Error400[400 Bad Request<br/>ValidationException]
    Validate -->|Valid| Service[Service Layer]
    Service -->|Job Not Found| Error404[404 Not Found<br/>JobNotFoundException]
    Service -->|Job Conflict| Error409[409 Conflict<br/>JobConflictException]
    Service -->|Automation Error| Error500[500 Internal Error<br/>AutomationException]
    Service -->|Success| Success[200 OK<br/>Response]

    Error400 --> Response[HTTP Response]
    Error404 --> Response
    Error409 --> Response
    Error500 --> Response
    Success --> Response

    style Error400 fill:#ffebee
    style Error404 fill:#ffebee
    style Error409 fill:#ffebee
    style Error500 fill:#ffebee
    style Success fill:#e8f5e9
```

## File Structure Overview

```mermaid
graph TD
    Root[FBP Project Root] --> App[app/]
    Root --> Tests[tests/]
    Root --> Docs[docs/]
    Root --> Config[Config Files]

    App --> Main[main.py<br/>FastAPI App]
    App --> Routers[routers/]
    App --> Services[services/]
    App --> Core[core/]
    App --> Utils[utils/]

    Routers --> R1[health.py]
    Routers --> R2[echo.py]
    Routers --> R3[nfa.py]
    Routers --> R4[nfa_real.py]
    Routers --> R5[redesim.py]

    Services --> S1[echo_service.py]
    Services --> S2[nfa_service.py]
    Services --> S3[nfa_real_service.py]
    Services --> S4[redesim_service.py]

    Core --> C1[config.py]
    Core --> C2[logger.py]
    Core --> C3[exceptions.py]
    Core --> C4[jobs.py]
    Core --> C5[clients.py]
    Core --> C6[browser.py]

    Tests --> T1[test_health.py]
    Tests --> T2[test_echo.py]
    Tests --> T3[test_nfa.py]
    Tests --> T4[test_nfa_real.py]
    Tests --> T5[test_redesim.py]

    Config --> CF1[pyproject.toml]
    Config --> CF2[requirements.txt]
    Config --> CF3[.env]
    Config --> CF4[run.sh]

    style App fill:#e1f5ff
    style Routers fill:#e1f5ff
    style Services fill:#f3e5f5
    style Core fill:#fff3e0
    style Tests fill:#e8f5e9
```


