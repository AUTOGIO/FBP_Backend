# ARCHITECTURAL CONTRACT — FBP Backend

**Status:** LOCKED — This document defines the canonical architectural boundaries for FBP Backend.  
**Last Updated:** 2025-01-27  
**Authority:** Principal Systems Engineer — Final System Consolidation

---

## 🎯 SYSTEM ROLE

**FBP Backend** is the **execution authority** for system automation.

### Core Responsibilities

1. **Execution Ownership**

   - Owns all execution logic, state, and lifecycle
   - Manages deterministic, resumable, long-running processes
   - Provides execution state tracking and recovery

2. **State Management**

   - Owns execution state (phases, checkpoints, recovery data)
   - Manages job metadata and execution relationships
   - Maintains in-memory state (extensible to persistence)

3. **Automation Execution**

   - Executes browser automation (Playwright)
   - Performs form filling, data extraction, PDF operations
   - Handles retries, error recovery, and self-healing

4. **Deterministic Behavior**
   - All execution is deterministic and resumable
   - No workflow semantics or orchestration logic
   - No background job frameworks or schedulers

---

## ✅ MUST (Required Behaviors)

- **MUST** own all execution logic and state
- **MUST** provide deterministic, resumable execution
- **MUST** track execution state (phases, checkpoints, recovery)
- **MUST** handle long-running processes with proper lifecycle management
- **MUST** expose execution state via API endpoints
- **MUST** support async I/O and controlled concurrency
- **MUST** optimize for ARM64-native Python behavior
- **MUST** provide error recovery and self-healing capabilities

---

## ❌ MUST NOT (Forbidden Patterns)

- **MUST NOT** delegate execution to external systems
- **MUST NOT** implement workflow engines or orchestration abstractions
- **MUST NOT** use background job frameworks (Celery, RQ, etc.)
- **MUST NOT** implement schedulers or worker pools
- **MUST NOT** own coordination logic (delegated to FoKS)
- **MUST NOT** implement CPU-bound parallelism
- **MUST NOT** store execution state outside FBP boundaries
- **MUST NOT** expose workflow/orchestrator terminology in execution layers

---

## 🔗 SYSTEM RELATIONSHIPS

### FBP ↔ FoKS Intelligence

- **FBP Role:** Execution authority
- **FoKS Role:** Control plane (coordinates and delegates)
- **Interface:** UNIX socket (`/tmp/fbp.sock`) or TCP (configurable)
- **Protocol:** HTTP-like requests with JSON payloads

**Boundary Rules:**

- FoKS **MUST** delegate execution to FBP
- FoKS **MUST NOT** execute automation directly
- FBP **MUST** accept execution requests from FoKS
- FBP **MUST NOT** coordinate multiple systems

### FBP ↔ n8n

- **FBP Role:** Execution provider
- **n8n Role:** Scheduling and triggering ONLY
- **Interface:** HTTP endpoints (health, nfa, redesim, etc.)

**Boundary Rules:**

- n8n **MUST** trigger FBP via HTTP requests
- n8n **MUST NOT** own execution state
- n8n **MUST NOT** implement execution logic
- FBP **MUST** respond to n8n triggers
- FBP **MUST NOT** depend on n8n for execution

---

## 🏗️ ARCHITECTURAL LAYERS

### Layer 1: Router (FastAPI)

- HTTP endpoints for external triggers
- Request validation and response formatting
- **MUST NOT** contain business logic

### Layer 2: Service (Execution Orchestration)

- Coordinates execution within FBP boundaries
- Manages execution state and lifecycle
- **MUST NOT** delegate to external execution systems

### Layer 3: Module (Business Logic)

- Domain-specific automation logic (NFA, REDESIM)
- Form filling, data extraction, PDF operations
- **MUST** be deterministic and resumable

### Layer 4: Core (Infrastructure)

- Execution state management
- Browser automation (Playwright)
- Job tracking and recovery
- **MUST** provide deterministic execution primitives

---

## 🔒 HARDWARE & OS CONSTRAINTS

**Target Environment:**

- Model: iMac (Mac15,5)
- Chip: Apple M3 (4P + 4E cores)
- Memory: 16 GB
- OS: macOS 26.0 Beta

**Optimization Requirements:**

- Async I/O (no blocking operations)
- Deterministic execution (no race conditions)
- Controlled concurrency (no worker pools)
- Long-running processes (proper lifecycle management)
- ARM64-native Python behavior

---

## 📋 ENFORCEMENT

This contract is enforced through:

1. **Documentation:** This contract document
2. **Code Comments:** Guardrails in execution modules
3. **Regression Warnings:** `docs/REGRESSION_WARNINGS.md`
4. **AI Guardrails:** `.cursor/ARCHITECTURAL_GUARDRAILS.md`

**Violations of this contract are architectural bugs, not features.**

---

## 🔄 EVOLUTION

This contract may evolve, but changes **MUST**:

- Preserve execution authority boundaries
- Maintain deterministic execution guarantees
- Respect hardware/OS constraints
- Be approved by Principal Systems Engineer

**Last Review:** 2025-01-27  
**Next Review:** As needed (architectural changes)
