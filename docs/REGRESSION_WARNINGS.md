# REGRESSION WARNINGS — Forbidden Patterns

**Status:** ACTIVE — This document lists patterns that violate architectural boundaries.  
**Last Updated:** 2025-01-27  
**Authority:** Principal Systems Engineer — Final System Consolidation

---

## 🚨 PURPOSE

This document serves as a **regression prevention guide** for FBP Backend. It lists forbidden patterns that violate the architectural contract, explains why they are dangerous, and provides detection patterns.

**Any pattern listed here is an architectural bug, not a feature.**

---

## ❌ FORBIDDEN PATTERNS

### 1. Workflow Engines and Orchestration Abstractions

**Pattern:**

- Importing or using workflow engines (Airflow, Prefect, Temporal, etc.)
- Creating orchestration abstractions (workflow, pipeline, dag, etc.)
- Implementing workflow state machines

**Why Forbidden:**

- FBP owns execution, not orchestration
- Workflow semantics violate deterministic execution guarantees
- Orchestration belongs to FoKS (control plane)

**Detection Patterns:**

```bash
# Search for workflow engine imports
grep -r "from.*workflow\|import.*workflow\|from.*airflow\|import.*airflow\|from.*prefect\|import.*prefect\|from.*temporal\|import.*temporal" app/

# Search for workflow terminology
grep -r "workflow\|pipeline\|dag\|orchestrat" app/ --include="*.py"
```

**Example Violations:**

```python
# ❌ FORBIDDEN: Workflow engine
from airflow import DAG
from prefect import flow, task

# ❌ FORBIDDEN: Orchestration abstraction
class WorkflowEngine:
    def execute_workflow(self, steps):
        ...

# ❌ FORBIDDEN: Pipeline terminology
class AutomationPipeline:
    def run_pipeline(self):
        ...
```

---

### 2. Background Job Frameworks

**Pattern:**

- Using Celery, RQ, Dramatiq, or similar background job frameworks
- Creating worker pools or task queues
- Implementing distributed task execution

**Why Forbidden:**

- FBP executes deterministically in owned async contexts
- Background job frameworks introduce non-deterministic execution
- Worker pools violate controlled concurrency requirements

**Detection Patterns:**

```bash
# Search for background job frameworks
grep -r "from.*celery\|import.*celery\|from.*rq\|import.*rq\|from.*dramatiq\|import.*dramatiq\|from.*huey\|import.*huey" app/

# Search for worker/task queue terminology
grep -r "worker\|task_queue\|job_queue\|background.*task" app/ --include="*.py"
```

**Example Violations:**

```python
# ❌ FORBIDDEN: Celery
from celery import Celery
app = Celery('fbp')

# ❌ FORBIDDEN: RQ
from rq import Queue
queue = Queue()

# ❌ FORBIDDEN: Worker pool
class WorkerPool:
    def __init__(self, num_workers):
        ...
```

---

### 3. Schedulers and Cron-like Systems

**Pattern:**

- Implementing schedulers (APScheduler, schedule, etc.)
- Creating cron-like scheduling logic
- Adding periodic task execution

**Why Forbidden:**

- Scheduling belongs to n8n (external trigger system)
- FBP executes on-demand, not on schedule
- Schedulers violate execution authority boundaries

**Detection Patterns:**

```bash
# Search for scheduler libraries
grep -r "from.*schedule\|import.*schedule\|from.*apscheduler\|import.*apscheduler\|from.*cron\|import.*cron" app/

# Search for scheduling terminology
grep -r "schedule\|cron\|periodic\|recurring" app/ --include="*.py"
```

**Example Violations:**

```python
# ❌ FORBIDDEN: Scheduler
import schedule
schedule.every(10).minutes.do(run_nfa)

# ❌ FORBIDDEN: APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
```

---

### 4. Execution Delegation to External Systems

**Pattern:**

- Delegating execution to external systems (FoKS, n8n, etc.)
- Creating execution proxies or wrappers
- Implementing execution routing outside FBP

**Why Forbidden:**

- FBP owns execution authority
- Delegation violates execution ownership
- External systems coordinate, not execute

**Detection Patterns:**

```bash
# Search for execution delegation
grep -r "delegate.*execution\|execute.*external\|proxy.*execution\|route.*execution" app/ --include="*.py"

# Search for external execution calls
grep -r "foks.*execute\|n8n.*execute\|external.*run" app/ --include="*.py" -i
```

**Example Violations:**

```python
# ❌ FORBIDDEN: Delegating execution
async def run_nfa(payload):
    return await foks_client.execute_nfa(payload)  # FBP should execute, not delegate

# ❌ FORBIDDEN: Execution proxy
class ExecutionProxy:
    def execute(self, task):
        return external_system.run(task)
```

---

### 5. State Ownership Outside FBP

**Pattern:**

- Storing execution state in external systems (FoKS, n8n, databases)
- Creating state synchronization with external systems
- Implementing distributed state management

**Why Forbidden:**

- FBP owns execution state
- External state ownership violates state management boundaries
- State synchronization creates coupling and non-determinism

**Detection Patterns:**

```bash
# Search for external state storage
grep -r "state.*external\|external.*state\|sync.*state\|distributed.*state" app/ --include="*.py" -i

# Search for state delegation
grep -r "foks.*state\|n8n.*state\|db.*execution.*state" app/ --include="*.py" -i
```

**Example Violations:**

```python
# ❌ FORBIDDEN: External state storage
async def save_execution_state(state):
    await foks_client.save_state(state)  # FBP should own state

# ❌ FORBIDDEN: State synchronization
class StateSync:
    def sync_with_external(self, state):
        ...
```

---

### 6. CPU-Bound Parallelism and Worker Pools

**Pattern:**

- Using multiprocessing or threading for CPU-bound work
- Creating worker pools or thread pools
- Implementing parallel execution with workers

**Why Forbidden:**

- FBP optimizes for async I/O, not CPU parallelism
- Worker pools violate controlled concurrency requirements
- CPU-bound parallelism is not needed for browser automation

**Detection Patterns:**

```bash
# Search for multiprocessing/threading
grep -r "from.*multiprocessing\|import.*multiprocessing\|from.*threading\|import.*threading\|ThreadPool\|ProcessPool" app/

# Search for worker pool terminology
grep -r "worker.*pool\|thread.*pool\|process.*pool\|parallel.*worker" app/ --include="*.py" -i
```

**Example Violations:**

```python
# ❌ FORBIDDEN: Multiprocessing
from multiprocessing import Pool
pool = Pool(processes=4)

# ❌ FORBIDDEN: Thread pool
from concurrent.futures import ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=4)
```

---

### 7. Coordination Logic in Execution Layers

**Pattern:**

- Implementing coordination logic in execution modules
- Creating decision-making logic about which system to use
- Adding routing or delegation logic in execution code

**Why Forbidden:**

- Coordination belongs to FoKS (control plane)
- Execution layers must be deterministic and focused
- Coordination logic violates separation of concerns

**Detection Patterns:**

```bash
# Search for coordination logic
grep -r "coordinate\|route.*to\|decide.*which\|choose.*system" app/ --include="*.py" -i

# Search for delegation logic in execution modules
grep -r "delegate\|forward.*to\|call.*foks\|call.*external" app/modules/ --include="*.py" -i
```

**Example Violations:**

```python
# ❌ FORBIDDEN: Coordination in execution module
async def execute_nfa(payload):
    if should_use_foks(payload):
        return await foks_client.run_nfa(payload)  # Coordination logic
    else:
        return await local_execution(payload)

# ❌ FORBIDDEN: Routing logic
class ExecutionRouter:
    def route(self, task):
        if task.type == "nfa":
            return foks_client.execute(task)  # Should execute locally
```

---

## 🔍 DETECTION WORKFLOW

### Automated Detection

Run these commands regularly to detect violations:

```bash
# Full regression scan
cd /Users/dnigga/Documents/FBP_Backend
./scripts/detect_regressions.sh  # Create this script if needed

# Manual scan
grep -r "workflow\|pipeline\|dag\|orchestrat\|celery\|rq\|schedule\|cron\|multiprocessing\|threading\|worker.*pool" app/ --include="*.py" -i
```

### Code Review Checklist

Before merging any PR, verify:

- [ ] No workflow engine imports
- [ ] No background job framework imports
- [ ] No scheduler imports
- [ ] No execution delegation to external systems
- [ ] No external state storage
- [ ] No CPU-bound parallelism
- [ ] No coordination logic in execution modules

---

## 🛠️ REMEDIATION

If a violation is detected:

1. **Identify the violation** using detection patterns
2. **Document the violation** in a regression report
3. **Remove the violation** following architectural contract
4. **Add regression test** to prevent future violations
5. **Update this document** if new patterns emerge

---

## 📋 MAINTENANCE

This document should be updated when:

- New forbidden patterns are discovered
- Architectural boundaries evolve (with approval)
- Detection patterns need refinement

**Last Review:** 2025-01-27  
**Next Review:** As needed (when violations are detected)
