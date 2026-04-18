# claude-swarm

claude-swarm is a deterministic multi-agent orchestration framework that runs one model through specialized roles (planner, researcher, coder, reviewer, tester, summarizer), executes role tasks as a dependency graph, and minimizes token usage through compression, routing, and cache reuse.

## Architecture

```text
User Task
   |
   v
Planner Agent
   |
   v
Execution Graph (DAG)
   |-------------------------|
   v                         v
Researcher/Coder/... (parallel-ready groups)
   |                         |
   |----------- merge -------|
               |
               v
Summarizer + Final Result
```

Core flow:
1. Planner produces JSON node plan.
2. Router validates assignments and creates DAG.
3. Controller executes topological batches.
4. Token optimizer compresses/prunes context and enforces budgets.
5. State store/cache preserves reusable outputs.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

```bash
python -m cli.swarm_cli run "build a web crawler"
python -m cli.swarm_cli run --pipeline code "implement sorting algorithms"
python -m cli.swarm_cli run --dry-run "analyze this codebase"
python -m cli.swarm_cli list-agents
python -m cli.swarm_cli show-graph "build a REST API"
python -m cli.swarm_cli clear-cache
```

## API Reference

### Core
- `core.swarm_controller.SwarmController.execute(task: str, dry_run: bool=False) -> SwarmResult`
- `core.swarm_controller.SwarmController.execute_node(node, context) -> NodeResult`
- `core.swarm_controller.SwarmController.merge_results(results: dict) -> str`
- `core.agent_registry.AgentRegistry.register/get/list_agents/capabilities`
- `core.task_router.TaskRouter.build_graph/parse_plan/route_agent`
- `core.state_store.StateStore.set/get/delete/clear_namespace`
- `core.token_optimizer.TokenOptimizer.compress/prune_context/deduplicate/enforce_budget`
- `core.execution_graph.ExecutionGraph.add_node/add_dependency/topological_sort/get_parallel_groups/detect_cycles/visualize`

### Agents
All agents derive from `agents.base_agent.BaseAgent` and require a user-provided `ModelInterface` implementation via `generate(system_prompt, user_prompt, max_tokens, temperature=0.0) -> str`.

### Memory
- `memory.vector_index.VectorIndex.add/search`
- `memory.context_cache.ContextCache` (LRU + disk)
- `memory.knowledge_store.KnowledgeStore` (JSON persistent KV, namespace and pattern search)

### Pipelines
- `pipelines.repo_build_pipeline.build_repo_build_pipeline`
- `pipelines.research_pipeline.build_research_pipeline`
- `pipelines.code_pipeline.build_code_pipeline`

## Configuration Reference

Configuration files in `configs/`:
- `swarm_config.yaml`: global execution settings, model defaults, output options
- `agent_limits.yaml`: per-agent token/rate limits
- `routing_rules.yaml`: routing keywords, skip conditionals, capability hints

## Pipeline Descriptions

- **repo_build_pipeline**: planner → researcher → coder → reviewer → tester → summarizer
- **research_pipeline**: planner → researcher → summarizer
- **code_pipeline**: planner → coder → reviewer → tester

## Token Optimization

`TokenOptimizer` applies deterministic optimizations without external tokenizer dependencies:
- word-based estimation (`len(text.split()) * 1.3`)
- deduplication of repeated context
- relevance pruning by task term overlap
- incremental context delivery (send diffs from previous context)
- hard per-agent and global budget enforcement

## Examples

- `examples/large_codebase_example.py`
- `examples/research_project_example.py`

## Performance Characteristics

Typical outcomes for large structured tasks:
- **Token reduction**: ~40–70% from pruning, compression, deduplication, and caching
- **Execution speed improvement**: ~3–10x when independent graph branches execute in batch order

