# Beaver's Choice / Munder Difflin Multi-Agent Inventory and Quoting System

## Problem Statement
Beaver's Choice Paper Company needed a text-based multi-agent system to improve three operational bottlenecks:
- Slow and inconsistent inventory checks
- Delayed/uneven quote generation
- Unreliable sales finalization due to stock and delivery constraints

Project constraints required:
- Maximum of 5 agents
- Agent orchestration using one recommended framework (`smolagents`, `pydantic-ai`, or `npcsh`)
- End-to-end evaluation using `quote_requests_sample.csv`
- Persisted outputs in `test_results.csv`

## Approach
The implemented system uses **pydantic-ai** with deterministic business logic and framework-style tool definitions.

### Why this architecture
The workflow was split into non-overlapping responsibilities so each business function is owned by one worker agent, while an orchestrator manages routing and final response assembly.

### Agent design (5 total)
1. `OrchestrationAgent`
- Delegates work to other agents, coordinates data flow, and assembles the final response.

2. `RequestParsingAgent`
- Parses incoming text into structured fields (items, quantities, dates, metadata, unknown tokens).

3. `InventoryAgent`
- Checks stock, computes shortages, determines reorders, estimates supplier delivery, and logs stock-order transactions.

4. `QuoteAgent`
- Computes pricing, applies discount strategy, and uses historical quote context for adjustments.

5. `FulfillmentAgent`
- Validates delivery feasibility and finalizes sales transactions if feasible.

## Solution Implementation
Main implementation file: `project_starter.py`

### Framework and API configuration
- Framework: `pydantic-ai`
- API routing: **Vocareum OpenAI proxy** (`https://openai.vocareum.com/v1`)
- Key loading: `.env` via `UDACITY_OPENAI_API_KEY`

### Tooling and helper function usage
All required starter helper functions are used through agent tool wrappers:
- `create_transaction`
- `get_all_inventory`
- `get_stock_level`
- `get_supplier_delivery_date`
- `get_cash_balance`
- `generate_financial_report`
- `search_quote_history`

### Data flow summary
`Request` -> `Parse` -> `Inventory/Reorder` -> `Quote` -> `Fulfillment` -> `Final response`

Supporting docs:
- `workflow_diagram.md`
- `design_notes.txt`
- `reflection_report.txt`
- `submission_checklist.md`

## Evaluation and Results
Evaluation used the full `quote_requests_sample.csv` request set.

Generated output:
- `test_results.csv`

Observed outcomes from current run:
- 20/20 requests processed
- 13 cash-balance changes
- 15 fulfilled requests (confirmed)
- 5 unfulfilled requests with explicit timing/availability reasons

This demonstrates the system handles both success and constraint-driven rejection paths while maintaining financial/inventory state.

## How We Did It (Execution Steps)
1. Built a 5-agent architecture and mapped responsibilities in `workflow_diagram.md`.
2. Implemented pydantic-ai-based agents with explicit tool definitions in `project_starter.py`.
3. Wired all required starter helper functions through tool wrappers.
4. Ran test scenarios using `quote_requests_sample.csv` and captured output in `test_results.csv`.
5. Validated rubric coverage through `submission_checklist.md` and documented analysis in `reflection_report.txt`.

## Local Run Instructions
From the `project` folder:

```bash
python3 -m pip install -r requirements.txt
```

Create `.env`:

```env
UDACITY_OPENAI_API_KEY=your_vocareum_key
```

Run:

```bash
python3 project_starter.py
```

Expected artifacts:
- `test_results.csv`
- Console logs for each request with cash/inventory updates and final report
