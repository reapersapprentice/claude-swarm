# 🐝 claude-swarm

**A multi-agent orchestration framework that coordinates specialized AI agents to plan, research, code, review, test, and summarize software tasks — all from a single command.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 69 passed](https://img.shields.io/badge/tests-69%20passed-brightgreen.svg)](#testing)

---

## Table of Contents

- [What Is claude-swarm?](#what-is-claude-swarm)
- [How It Works — The Big Picture](#how-it-works--the-big-picture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [The Six Agents — What Each One Does](#the-six-agents--what-each-one-does)
- [Pipelines — Pre-Built Workflows](#pipelines--pre-built-workflows)
- [How Tasks Flow Through the System](#how-tasks-flow-through-the-system)
- [Token Optimization — Saving Money on API Calls](#token-optimization--saving-money-on-api-calls)
- [Memory and Caching — How Results Are Reused](#memory-and-caching--how-results-are-reused)
- [Using Any AI Model](#using-any-ai-model)
- [Configuration](#configuration)
- [Project Structure Explained](#project-structure-explained)
- [Examples](#examples)
- [Testing](#testing)
- [Contributing](#contributing)

---

## What Is claude-swarm?

When you ask an AI model to do something complex — like "build me a REST API" — you typically get one big response that tries to do everything at once. It might miss edge cases, skip testing, or produce code that wasn't thought through.

**claude-swarm takes a different approach.** Instead of relying on a single prompt, it breaks your task into stages and assigns each stage to a specialized agent. Think of it like a small software team:

1. One agent **plans** how to approach the task
2. Another **researches** relevant patterns and context
3. A third **writes the code**
4. Another **reviews** it for bugs
5. One **writes tests**
6. And a final agent **summarizes** everything into a clean deliverable

Each agent has its own system prompt, its own token budget, and its own role. The framework coordinates them automatically — you just describe what you want built.

**Who is this for?**
- Developers who use LLM APIs (Claude, GPT, etc.) in their projects and want more structured, reliable output
- Teams building AI-assisted development tools
- Anyone experimenting with multi-agent workflows

**What you need to know beforehand:**
- Basic Python (3.9+)
- A general understanding of what LLM APIs do (you send a prompt, you get text back)
- That's it — no ML background required

---

## How It Works — The Big Picture

Here's the high-level flow. Don't worry — each piece is explained in detail below.

```
You describe a task (e.g., "build a web crawler")
        │
        ▼
┌──────────────┐
│   Planner    │  Breaks the task into smaller steps with dependencies
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Task Router  │  Validates the plan and builds an execution graph (DAG)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────┐
│  Agents execute in dependency order               │
│                                                   │
│  Step 1: Researcher gathers context               │
│  Step 2: Coder writes implementation              │
│  Step 3: Reviewer checks for issues               │
│  Step 4: Tester generates test cases              │
│  (Steps without dependencies can run in parallel) │
└──────────────────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  Summarizer  │  Merges all outputs into one clean result
└──────┬───────┘
       │
       ▼
   Final result with merged output, token metrics, and graph visualization
```

**Key concept — the DAG (Directed Acyclic Graph):**

The planner's output is turned into a graph of steps. Each step says "I need these other steps to finish first." This is called a DAG — a standard computer science structure that prevents circular dependencies and determines what can run in parallel. If step A and step B don't depend on each other, they can run at the same time.

---

## Installation

### Requirements

- Python 3.9 or higher
- `pip` (Python's package manager)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/reapersapprentice/claude-swarm.git

# 2. Enter the project directory
cd claude-swarm

# 3. Install in development mode
pip install -e .
```

This installs two core dependencies:
- **PyYAML** — for reading configuration files
- **tiktoken** — for accurate token counting (falls back to a word-based estimate if unavailable)

### Optional: Semantic Search with ChromaDB

If you want richer memory capabilities (explained in the [Memory](#memory-and-caching--how-results-are-reused) section), install the optional vector search backend:

```bash
pip install -e ".[vectors]"
```

This adds **ChromaDB**, an open-source vector database. It's entirely optional — the framework includes a built-in vector search that works without it.

---

## Quick Start

### From the Command Line

The CLI is located in `cli/swarm_cli.py`. Here are the main commands:

```bash
# Run a task through the full pipeline (plan → research → code → review → test → summarize)
python -m cli.swarm_cli run "build a REST API with authentication"

# Run with a specific pipeline (explained below)
python -m cli.swarm_cli run --pipeline code "implement a binary search tree"
python -m cli.swarm_cli run --pipeline research "compare SQL vs NoSQL for session storage"

# Preview the execution graph without actually running anything (useful for debugging)
python -m cli.swarm_cli run --dry-run "refactor the database layer"

# List all registered agents and their names
python -m cli.swarm_cli list-agents

# Show the execution graph for a task as ASCII art
python -m cli.swarm_cli show-graph "build a microservice"

# Clear the result cache (start fresh)
python -m cli.swarm_cli clear-cache
```

The output is JSON, which includes:
- `success` — whether the pipeline completed without errors
- `merged_output` — the combined output from all agents
- `metrics` — token usage, duration, cache hits, and number of nodes executed

### From Python Code

```python
from pipelines import build_repo_build_pipeline

# Create a controller. Pass your own model, or omit for the built-in EchoModel (for testing).
controller = build_repo_build_pipeline(my_model)

# Run the full pipeline
result = controller.execute("build a web crawler with rate limiting")

# Inspect the results
print(result.success)              # True or False
print(result.merged_output)        # All agent outputs merged together
print(result.metrics)              # {"tokens_used": ..., "duration_seconds": ..., ...}
print(result.graph_visualization)  # ASCII diagram of the execution graph
print(result.node_results)         # Individual results from each agent
```

> **Note:** The built-in `EchoModel` returns deterministic placeholder outputs. It's useful for testing the framework itself without making API calls. To do real work, pass in your own model backend (see [Using Any AI Model](#using-any-ai-model)).

---

## The Six Agents — What Each One Does

Each agent is a Python class that inherits from `BaseAgent`. They all follow the same pattern:

1. Receive a task description and context from previous agents
2. Build a prompt using a system prompt loaded from `prompts/*.md`
3. Call the language model
4. Parse the model's response into structured JSON
5. Return an `AgentResult` with the parsed data and token usage

Here's what each agent is responsible for:

### 🧠 Planner (`agents/planner_agent.py`)

**Job:** Break a high-level task into smaller, ordered steps.

**How it works:** The planner asks the language model to decompose the task into a JSON array of nodes. Each node has:
- An `id` (e.g., `"research"`, `"code"`)
- An `agent` assignment (which agent should handle it)
- A `task` description
- A list of `dependencies` (which other nodes must complete first)

**Example output:**
```json
[
  {"id": "research", "agent": "researcher", "task": "Research rate limiting patterns", "dependencies": []},
  {"id": "code", "agent": "coder", "task": "Implement the crawler", "dependencies": ["research"]},
  {"id": "review", "agent": "reviewer", "task": "Review the implementation", "dependencies": ["code"]},
  {"id": "test", "agent": "tester", "task": "Write tests", "dependencies": ["review"]},
  {"id": "summary", "agent": "summarizer", "task": "Summarize everything", "dependencies": ["test"]}
]
```

**Safety net:** If the model returns invalid JSON, the planner generates a sensible default plan (research → code → review → test → summarize).

### 🔍 Researcher (`agents/researcher_agent.py`)

**Job:** Gather context, analyze patterns, and understand the problem before code is written.

**Output format:** `{"findings": [...], "sources": [...], "summary": "..."}`

This agent is about understanding the "what" and "why" before jumping to "how."

### 💻 Coder (`agents/coder_agent.py`)

**Job:** Write actual code with file paths and explanations.

**Output format:** `{"files": [{"path": "...", "content": "..."}], "explanation": "..."}`

The coder produces structured output — not just a code block, but file paths and descriptions so you know where everything goes.

### 🔎 Reviewer (`agents/reviewer_agent.py`)

**Job:** Audit the code for bugs, security issues, and quality problems.

**Output format:** `{"issues": [...], "approved": true/false, "suggestions": [...]}`

### 🧪 Tester (`agents/tester_agent.py`)

**Job:** Generate test cases that validate the implementation.

**Output format:** `{"tests": [{"name": "...", "code": "..."}], "coverage_notes": "..."}`

### 📋 Summarizer (`agents/summarizer_agent.py`)

**Job:** Compress all previous outputs into a single, clean deliverable.

**Output format:** `{"summary": "...", "highlights": [...]}`

### How Agents Handle Errors

Every agent has a `_parse` method that tries to parse the model's raw output as JSON. If parsing fails (bad JSON, missing fields, etc.), it falls back to a safe default structure. This means the pipeline never crashes from a malformed model response — it gracefully degrades.

---

## Pipelines — Pre-Built Workflows

A pipeline is a pre-configured combination of agents. You pick a pipeline, and the framework wires up the right agents in the right order.

### `repo_build` — Full Engineering Workflow (default)

```
Planner → Researcher → Coder → Reviewer → Tester → Summarizer
```

Use this when you want the complete treatment: plan the approach, research first, write code, review it, test it, and summarize.

```bash
python -m cli.swarm_cli run "build a user authentication system"
```

### `research` — Analysis Only

```
Planner → Researcher → Summarizer
```

Use this when you need research and analysis, not code. Good for technical investigations, comparisons, or feasibility studies.

```bash
python -m cli.swarm_cli run --pipeline research "compare WebSocket vs SSE for real-time updates"
```

### `code` — Build Without Research

```
Planner → Coder → Reviewer → Tester
```

Use this when you already know what you want and just need it implemented and verified.

```bash
python -m cli.swarm_cli run --pipeline code "implement a priority queue with decrease-key"
```

### Building Custom Pipelines

You can create your own pipeline by wiring up the `SwarmController` directly. The `pipelines/common.py` module has helper functions (`build_controller`, `build_registry`) that construct the controller with all necessary components. You define which agents to register and what dependencies exist between nodes.

---

## How Tasks Flow Through the System

Let's trace exactly what happens when you run a task. This section explains the internals.

### Step 1: The Planner Creates a Plan

The `SwarmController.execute()` method starts by calling the planner agent. The planner sends your task to the language model, which returns a JSON list of steps (nodes). Each node specifies what agent should handle it and which other nodes it depends on.

### Step 2: The Task Router Builds an Execution Graph

The `TaskRouter` takes the planner's output and constructs an `ExecutionGraph` — a DAG (directed acyclic graph). During this process, it:

- **Validates the plan** — every node must have an `id` and a `task`
- **Assigns agents** — if a node doesn't specify an agent, the router infers one from keyword-based routing rules (configured in `configs/routing_rules.yaml`). For example, a task containing the word "implement" is routed to the coder agent.
- **Checks for cycles** — if step A depends on step B and step B depends on step A, that's a cycle. The graph rejects it.
- **Validates capability compatibility** — each agent declares capabilities (like "code", "review", "test"). The router checks that the task matches the agent's capabilities.

### Step 3: Agents Execute in Parallel Groups

The graph is divided into "parallel groups" — batches of nodes that can run at the same time because they have no dependencies on each other.

For each node in each group:

1. **Context assembly** — outputs from dependency nodes are gathered
2. **Retrieval pipeline** (optional) — if configured, relevant past results are fetched from the vector store and injected into the context
3. **Token optimization** — the `TokenOptimizer` deduplicates, prunes, and compresses the context
4. **Cache check** — if this exact task/context combination was seen before, the cached result is returned instantly
5. **Agent execution** — the agent builds a prompt (system prompt + user prompt) and calls the language model
6. **Output compression** (optional) — the `CompressionPipeline` can further reduce the output before passing it downstream
7. **Budget enforcement** — token usage is checked against per-agent and global limits
8. **Result storage** — the output is stored in the cache and (optionally) indexed in the vector store

### Step 4: Retry and Skip Logic

- **Retries:** If a node fails (exception, timeout, etc.), it's retried automatically. The number of retries is configurable (default: 2).
- **Optional nodes:** Nodes can be marked as `optional`. If an optional node fails after retries, it's skipped and the pipeline continues. Required nodes that fail halt the pipeline.

### Step 5: Results Are Merged

The `SwarmController.merge_results()` method combines outputs from all successful nodes into a single string, sorted by node ID. The final `SwarmResult` includes:

- `success` — `True` if all required nodes completed
- `merged_output` — the combined text from all agents
- `node_results` — individual results per node (output, tokens used, whether it was cached, errors)
- `metrics` — total tokens used, execution duration, cache hits, nodes executed
- `graph_visualization` — an ASCII representation of the execution graph

### Hooks

You can attach callbacks that run before or after each node executes:

```python
controller.add_pre_task_hook(lambda node, context: print(f"Starting: {node.id}"))
controller.add_post_task_hook(lambda node, result: print(f"Finished: {node.id}, success={result.success}"))
```

This is useful for logging, monitoring, or custom integrations.

---

## Token Optimization — Saving Money on API Calls

LLM API calls are priced by tokens (roughly, words). If you send the same context to every agent, you waste tokens — and money. The `TokenOptimizer` (`core/token_optimizer.py`) applies several strategies to reduce token usage:

### 1. Deduplication

When context is assembled from multiple sources, near-identical paragraphs are detected using sequence matching and removed. This prevents the same information from being sent twice.

### 2. Relevance Pruning

Each paragraph in the context is scored against the current task using keyword overlap. Low-relevance paragraphs are dropped. The remaining paragraphs are kept in order of relevance until the token budget is filled.

### 3. Incremental Context

The optimizer tracks what context each agent has already seen. On subsequent calls, it sends only the new content (the "diff"), not the full history. This is especially effective in multi-step pipelines where context grows over time.

### 4. Budget Enforcement

Each agent has a token limit (configurable in `configs/agent_limits.yaml`). There's also a global limit across all agents (default: 50,000 tokens). If a call would exceed either limit, a `ValueError` is raised before the API call is made — so you never accidentally run up a large bill.

### 5. Token Estimation

Tokens are estimated using the `tiktoken` library when available (accurate, model-specific counting). If `tiktoken` isn't available, it falls back to a `words × 1.3` approximation — fast and dependency-free.

### 6. Subscription Tier Awareness

If you're on a Claude Pro (or similar) subscription, you probably don't want to exceed your plan limits and get charged for overage. The **Subscription Rate Limiter** (`token_infra/subscription.py`) enforces plan-level guardrails:

- **Per-minute rate limits** — prevents bursts of requests that exceed your plan's API rate cap.
- **Daily token caps** — tracks cumulative token usage across all agents and stops execution before you go over your daily allowance.
- **Per-request token ceilings** — clamps the `max_tokens` parameter on every API call so no single response can blow through your budget.

**Available tiers:**

| Tier | Requests/min | Daily token cap | Max tokens/request |
|------|-------------|-----------------|-------------------|
| `free` | 5 | 25,000 | 1,024 |
| `pro` | 25 | 300,000 | 4,096 |
| `team` | 50 | 1,000,000 | 8,192 |
| `unlimited` | 120 | No cap | 16,384 |

**Set your tier** in `configs/swarm_config.yaml`:

```yaml
subscription:
  tier: "pro"
```

Or override from the command line:

```bash
python -m cli.swarm_cli run --subscription-tier pro "build a REST API"
```

You can also customize individual limits while keeping the tier defaults for everything else:

```yaml
subscription:
  tier: "pro"
  daily_token_cap: 150000      # more conservative than the default 300k
  requests_per_minute: 15      # slower pace
```

**Check your current usage** at any time:

```bash
python -m cli.swarm_cli subscription-status
```

**From Python code**, pass a `SubscriptionRateLimiter` to the `ClaudeAdapter`:

```python
from token_infra.subscription import SubscriptionRateLimiter
from token_infra.adapters.claude_adapter import ClaudeAdapter

limiter = SubscriptionRateLimiter(tier="pro")
adapter = ClaudeAdapter(subscription_limiter=limiter)
```

The limiter is thread-safe and handles automatic backoff — if you hit the per-minute rate limit, `wait_if_needed()` pauses until capacity is available instead of failing. Daily caps are hard limits that raise a `SubscriptionError` to prevent unexpected charges.

### Token Infrastructure Layer

For more advanced prompt management, the `token_infra/` package provides additional tools:

- **PromptBuilder** (`token_infra/prompt_builder.py`) — Assembles prompts from YAML-defined templates, roles, and rulesets (defined in `configs/prompt_schema.yaml`). This ensures prompts are deterministic and consistent across runs.
- **TokenBudget** (`token_infra/token_budget.py`) — Per-agent budget validation with named profiles (e.g., "strict" at 800 tokens, "extended" at 8000 tokens). Profiles are defined in `configs/budgets.yaml`.
- **CompressionPipeline** (`token_infra/compression.py`) — Deduplicates and prunes inter-agent outputs before they're passed downstream.
- **RetrievalPipeline** (`token_infra/retrieval_pipeline.py`) — Queries the vector store for semantically similar past results and injects them into the current prompt.
- **VectorStore** (`token_infra/vector_store.py`) — Dual-backend semantic search. Uses ChromaDB when installed, otherwise falls back to the built-in bag-of-words cosine similarity index.
- **SubscriptionRateLimiter** (`token_infra/subscription.py`) — Plan-aware rate limiting and daily token caps (see above).

To enable the full token infrastructure, pass a `token_config` when building a pipeline:

```python
controller = build_repo_build_pipeline(
    my_model,
    token_config={
        "prompt_schema_path": "configs/prompt_schema.yaml",
        "budgets_path": "configs/budgets.yaml",
        "prefer_chromadb": False,   # Use built-in vector search
        "retrieval_top_k": 3,       # Inject top 3 similar past results
    }
)
```

---

## Memory and Caching — How Results Are Reused

claude-swarm includes three layers of memory, all working without external services:

### StateStore (`core/state_store.py`)

A JSON-backed key-value store with **namespaces** and **TTL (time-to-live) expiration**.

- The swarm controller uses it to cache agent results. If you run the same task with the same context twice, the second run returns instantly from cache.
- Data is organized by namespace (e.g., `"results"`) so different types of data don't collide.
- Entries can expire automatically after a configurable number of seconds.
- State is persisted to `.swarm_state.json` on disk, so it survives restarts.

### ContextCache (`memory/context_cache.py`)

An **LRU (Least Recently Used) cache** for agent outputs.

- Keyed by a SHA-256 hash of the agent name, task, and context — so identical inputs always produce a cache hit.
- Has a configurable max size (default: 128 entries). When full, the least recently used entry is evicted.
- Persisted to disk as JSON.

### VectorIndex (`memory/vector_index.py`)

A **built-in similarity search** engine with zero external dependencies.

- Converts text into sparse bag-of-words vectors
- Uses cosine similarity to find the most relevant past results for a new query
- No API calls, no database — everything runs in-memory with plain Python

This is what powers the retrieval pipeline when ChromaDB isn't installed.

### KnowledgeStore (`memory/knowledge_store.py`)

A **namespaced key-value store** for long-term knowledge across sessions.

- Supports wildcard search (e.g., find all keys matching `"auth_*"`)
- Persisted to `knowledge_store/store.json`
- Useful for storing project-specific context that agents can reference later

---

## Using Any AI Model

claude-swarm doesn't lock you into any specific AI provider. It works with any model backend through the `ModelInterface` protocol — a single method you need to implement:

```python
from agents.base_agent import ModelInterface

class MyModel(ModelInterface):
    def generate(
        self,
        system_prompt: str,    # Instructions for the model's role
        user_prompt: str,      # The actual task + context
        max_tokens: int,       # Maximum response length
        temperature: float = 0.0  # Randomness (0.0 = deterministic)
    ) -> str:
        # Call your model here and return the response as a string
        return my_api.call(system_prompt, user_prompt, max_tokens)
```

**That's the only method.** The framework handles everything else — prompt construction, routing, caching, compression, retries, and result merging.

### Example: Using Claude via the Anthropic API

```python
import anthropic

class ClaudeBackend(ModelInterface):
    def __init__(self):
        self.client = anthropic.Anthropic()

    def generate(self, system_prompt, user_prompt, max_tokens, temperature=0.0):
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text
```

### Example: Using OpenAI's API

```python
import openai

class GPTBackend(ModelInterface):
    def __init__(self):
        self.client = openai.OpenAI()

    def generate(self, system_prompt, user_prompt, max_tokens, temperature=0.0):
        response = self.client.chat.completions.create(
            model="gpt-4",
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
```

### Built-in EchoModel (For Testing)

The framework includes an `EchoModel` in `pipelines/common.py` that returns deterministic placeholder responses without making any API calls. It's used in tests and is the default when you don't pass a model. This lets you explore the framework's structure and behavior without needing an API key.

---

## Configuration

All configuration is stored as YAML files in the `configs/` directory. Here's what each file controls:

### `configs/swarm_config.yaml` — Global Settings

```yaml
swarm:
  max_total_tokens: 50000     # Global token budget across all agents
  max_execution_time: 300     # Timeout in seconds
  retry_failed_nodes: true    # Automatically retry failed steps
  max_retries: 2              # How many times to retry
  cache_results: true         # Cache results for reuse

model:
  provider: "claude"
  default_model: "claude-sonnet-4-20250514"
  temperature: 0.0            # 0.0 = deterministic output

output:
  format: "structured"
  include_metrics: true
  save_artifacts: true
  artifacts_dir: ".swarm_output"
```

### `configs/agent_limits.yaml` — Per-Agent Token Budgets

Each agent gets its own token limit and budget profile:

```yaml
planner:
  max_tokens: 3000
  budget_profile: standard    # Uses 2000 prompt / 1500 response limits

coder:
  max_tokens: 7000
  budget_profile: extended    # Uses 8000 prompt / 4096 response limits

reviewer:
  max_tokens: 4000
  budget_profile: strict      # Uses 800 prompt / 600 response limits
```

### `configs/budgets.yaml` — Budget Profile Definitions

Profiles define prompt and response limits for each agent category:

```yaml
strict:
  prompt_limit: 800
  response_limit: 600
  soft_ratio: 0.80

standard:
  prompt_limit: 2000
  response_limit: 1500
  soft_ratio: 0.85

extended:
  prompt_limit: 8000
  response_limit: 4096
  soft_ratio: 0.90
```

### `configs/routing_rules.yaml` — Agent Assignment Rules

When the planner doesn't specify which agent should handle a step, the task router uses keyword matching:

```yaml
default_agent: researcher     # Fallback when no keyword matches

conditional:
  - keyword: "implement"
    agent: coder
  - keyword: "test"
    agent: tester
  - keyword: "review"
    agent: reviewer

skip_if_contains:
  test: "no tests required"   # Skip the test node if findings contain this phrase
```

### `configs/prompt_schema.yaml` — Prompt Templates

Defines reusable templates, role descriptions, and rulesets that the `PromptBuilder` assembles into prompts:

```yaml
templates:
  TMP:PLAN: |
    Task: {task}
    Context: {context}
    Decompose into atomic execution nodes.

role_blocks:
  ROLE_PLANNER: "You are a planning specialist producing deterministic execution DAGs."
  ROLE_CODER: "You are a coding specialist producing production-grade implementation artifacts."

rulesets:
  T1: "Use concise, deterministic phrasing."
  T5: "Prioritize correctness over verbosity."
```

---

## Project Structure Explained

```
claude-swarm/
│
├── core/                       The orchestration engine
│   ├── swarm_controller.py     Runs the full pipeline: plan → execute → merge
│   ├── execution_graph.py      DAG data structure with cycle detection and parallel grouping
│   ├── task_router.py          Converts planner output into a validated execution graph
│   ├── token_optimizer.py      Deduplication, pruning, incremental diffs, budget enforcement
│   ├── agent_registry.py       Registers and lazily initializes agents by name
│   └── state_store.py          JSON-backed persistent state with namespaces and TTL
│
├── agents/                     The six specialized agents
│   ├── base_agent.py           Abstract base class with caching, prompt loading, and model calls
│   ├── planner_agent.py        Breaks tasks into execution node graphs
│   ├── researcher_agent.py     Gathers context and findings
│   ├── coder_agent.py          Produces structured code with file paths
│   ├── reviewer_agent.py       Audits code for bugs and security issues
│   ├── tester_agent.py         Generates test cases
│   └── summarizer_agent.py     Compresses outputs into a final deliverable
│
├── token_infra/                Advanced token management
│   ├── prompt_builder.py       Builds prompts from YAML-defined schemas
│   ├── token_budget.py         Per-agent token budget validation
│   ├── compression.py          Deduplication and relevance pruning for inter-agent context
│   ├── retrieval_pipeline.py   Injects relevant past results into prompts via vector search
│   └── vector_store.py         Semantic search with ChromaDB or built-in fallback
│
├── memory/                     Result caching and retrieval
│   ├── vector_index.py         In-memory bag-of-words similarity search (no dependencies)
│   ├── context_cache.py        LRU cache with disk persistence
│   └── knowledge_store.py      Namespaced key-value store for cross-session knowledge
│
├── pipelines/                  Pre-configured agent workflows
│   ├── repo_build_pipeline.py  Full 6-agent pipeline (plan → research → code → review → test → summarize)
│   ├── research_pipeline.py    3-agent pipeline (plan → research → summarize)
│   ├── code_pipeline.py        4-agent pipeline (plan → code → review → test)
│   └── common.py               Shared setup: model defaults, registry builder, controller factory
│
├── utils/                      Shared utilities
│   ├── diff_manager.py         Generate and apply unified diffs between text versions
│   ├── dependency_mapper.py    Extract Python import graphs using AST parsing
│   ├── chunker.py              Split text into token-budget-aware chunks with overlap
│   └── logger.py               Structured JSON logging
│
├── configs/                    YAML configuration files (described above)
├── prompts/                    System prompts for each agent (Markdown files)
├── cli/                        Command-line interface
├── examples/                   Runnable example scripts
└── tests/                      pytest test suite (69 tests)
```

---

## Examples

The `examples/` directory contains runnable scripts that demonstrate different use cases.

### Full Pipeline Example

```python
# examples/large_codebase_example.py
from pipelines.repo_build_pipeline import build_repo_build_pipeline

controller = build_repo_build_pipeline()  # Uses built-in EchoModel
result = controller.execute("Build a modular service-oriented application architecture")
print(result.merged_output)
```

### Research Example

```python
# examples/research_project_example.py
from pipelines.research_pipeline import build_research_pipeline

controller = build_research_pipeline()
result = controller.execute("Research state-of-the-art approaches for retrieval-augmented generation")
print(result.merged_output)
```

### Token-Optimized Pipeline

```python
# examples/token_optimized_pipeline.py
from pipelines.repo_build_pipeline import build_repo_build_pipeline

# Run without token infrastructure
baseline = build_repo_build_pipeline()
baseline_result = baseline.execute("Implement repository bootstrap workflow with tests")

# Run with full token infrastructure enabled
optimized = build_repo_build_pipeline(
    token_config={
        "prompt_schema_path": "configs/prompt_schema.yaml",
        "budgets_path": "configs/budgets.yaml",
        "prefer_chromadb": False,
        "retrieval_top_k": 3,
    }
)
optimized_result = optimized.execute("Implement repository bootstrap workflow with tests")

# Compare token usage
print(f"Baseline tokens: {baseline_result.metrics.get('tokens_used', 0)}")
print(f"Optimized tokens: {optimized_result.metrics.get('tokens_used', 0)}")
```

---

## Testing

The project includes 69 tests covering every major component. Run them with:

```bash
pytest -v
```

The tests use the built-in `EchoModel`, so they don't require any API keys or network access. They complete in under 5 seconds.

**What's tested:**

| Test File | What It Covers |
|-----------|---------------|
| `test_agent_parse_safety.py` | All 6 agents handle malformed model responses gracefully |
| `test_agent_registry.py` | Agent registration, lazy initialization, duplicate detection |
| `test_cli.py` | Command-line argument parsing and command dispatch |
| `test_context_cache.py` | LRU eviction, disk persistence, key generation |
| `test_controller_error_paths.py` | Pre/post hooks, retry logic, cache hits, dry-run mode |
| `test_diff_manager.py` | Unified diff generation and patch application |
| `test_execution_graph.py` | DAG cycle detection, topological sorting, parallel groups |
| `test_pipelines.py` | End-to-end pipeline integration |
| `test_prompt_builder_extended.py` | Template assembly, encoding fallback, ruleset handling |
| `test_state_store_extended.py` | TTL expiration, namespace isolation, persistence |
| `test_swarm_controller.py` | Full execution flow, result merging, metric collection |
| `test_task_router.py` | Plan parsing, keyword routing, capability validation |
| `test_token_infra.py` | Prompt builder, token budget, retrieval pipeline integration |
| `test_token_optimizer.py` | Deduplication, pruning, budget enforcement |
| `test_vector_store_extended.py` | Similarity search, metadata storage, backend selection |

---

## Contributing

Contributions are welcome. Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes and add tests for new functionality
4. Run the full test suite: `pytest -v`
5. Submit a pull request

### Guidelines

- All new functionality should have corresponding tests
- Follow the existing code style (type hints, docstrings, `from __future__ import annotations`)
- Keep dependencies minimal — avoid adding new packages unless there's a strong reason

---

## License

MIT — see [LICENSE](LICENSE) for details.
