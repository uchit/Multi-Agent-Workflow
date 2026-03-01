# Beaver's Choice / Munder Difflin Multi-Agent Workflow

## Agent Inventory (Max 5)

1. `OrchestrationAgent`
2. `RequestParsingAgent`
3. `InventoryAgent`
4. `QuoteAgent`
5. `FulfillmentAgent`

Total agents: **5** (meets project constraint).

## Implementation Match (Diagram -> Code)

| Diagram Agent | Implemented Class in `project_starter.py` | Primary method used in orchestration |
|---|---|---|
| `OrchestrationAgent` | `OrchestrationAgent` | `handle_request(...)` |
| `RequestParsingAgent` | `RequestParsingAgent` | `parse(...)` |
| `InventoryAgent` | `InventoryAgent` | `check_and_reorder(...)`, `answer_inventory_question(...)` |
| `QuoteAgent` | `QuoteAgent` | `build_quote(...)` |
| `FulfillmentAgent` | `FulfillmentAgent` | `finalize(...)` |

This is a 1:1 architecture match between the submitted diagram and implementation.

## Agent Responsibilities (No Overlap)

| Agent | Owns | Does Not Own |
|---|---|---|
| `OrchestrationAgent` | Sequencing, routing, final response assembly | Parsing details, pricing math, stock math, transaction writes |
| `RequestParsingAgent` | Extract request intent, dates, items, metadata, unknown-item flags | Inventory checks, reordering, quote generation, fulfillment decisions |
| `InventoryAgent` | Stock checks, shortage detection, reorder sizing, reorder ETA, inventory-only answers | Pricing, discounting, sales confirmation |
| `QuoteAgent` | Line-item pricing, discount strategy, history-informed quote amount | Stock mutation, delivery feasibility, transaction posting |
| `FulfillmentAgent` | Delivery feasibility decision and sales transaction creation | Parsing, reordering policy, quote calculation |

## Agent-Tool Map (Purpose + Starter Helper Functions)

| Agent | Tool | Purpose | Starter helper function(s) used |
|---|---|---|---|
| `RequestParsingAgent` | `ParseRequestTool` | Convert free text into structured request payload (`request_date`, `delivery_date`, `items`, `metadata`) | No DB helper; text parsing utilities in agent |
| `InventoryAgent` | `InventorySnapshotTool` | Return inventory snapshot for inventory-only questions | `get_all_inventory(as_of_date)` |
| `InventoryAgent` | `StockCheckTool` | Calculate current stock per requested item | `get_stock_level(item_name, as_of_date)` |
| `InventoryAgent` | `ReorderPlanningTool` | Create stock order transactions for shortages and estimate arrival date | `get_supplier_delivery_date(input_date_str, quantity)`, `create_transaction(...)`, `get_cash_balance(as_of_date)` |
| `QuoteAgent` | `QuoteHistoryTool` | Retrieve similar historical quotes to adjust discounting | `search_quote_history(search_terms, limit)` |
| `QuoteAgent` | `QuotePricingTool` | Build subtotal, discount, and final quoted total | Uses catalog + history tool result (no direct DB helper write) |
| `FulfillmentAgent` | `DeliveryFeasibilityTool` | Decide whether all quoted items can meet requested delivery date | Uses `inventory_result` availability dates from `InventoryAgent` |
| `FulfillmentAgent` | `SalesExecutionTool` | Create sales transactions once feasible | `create_transaction(...)` |
| `OrchestrationAgent` | `FinancialStateViewTool` | Retrieve financial/inventory state before and after each request | `generate_financial_report(as_of_date)` |

## Orchestration + Agent/Tool Interaction Diagram

```mermaid
flowchart TD
    U[Incoming text request] --> O[OrchestrationAgent]

    O --> P[RequestParsingAgent]
    P --> PT[ParseRequestTool]
    PT -->|Output: ParsedRequest| P
    P -->|ParsedRequest| O

    O --> I[InventoryAgent]
    O -->|Input: ParsedRequest| I
    I --> IS[InventorySnapshotTool\nget_all_inventory()]
    I --> SC[StockCheckTool\nget_stock_level()]
    I --> RP[ReorderPlanningTool\nget_cash_balance() + get_supplier_delivery_date() + create_transaction()]
    I -->|Output: InventoryResult\nstock/shortage/reorder_actions/availability_date| O

    O --> Q[QuoteAgent]
    O -->|Input: ParsedRequest + InventoryResult| Q
    Q --> QH[QuoteHistoryTool\nsearch_quote_history()]
    Q --> QP[QuotePricingTool\nsubtotal/discount/total]
    QH -->|historical matches| QP
    Q -->|Output: QuoteResult\nline_items/subtotal/discount/total| O

    O --> F[FulfillmentAgent]
    O -->|Input: ParsedRequest + InventoryResult + QuoteResult| F
    F --> DF[DeliveryFeasibilityTool\nuses availability_date]
    F --> SE[SalesExecutionTool\ncreate_transaction()]
    DF -->|feasible?| SE
    F -->|Output: FulfillmentResult\nconfirmed or pending_restock| O

    O --> FS[FinancialStateViewTool\ngenerate_financial_report()]
    FS -->|state snapshot| O
    O --> R[Final customer response + updated state]
```

## Data Contracts Between Agents

- `OrchestrationAgent -> RequestParsingAgent`
  - Input: raw customer request text
  - Output: `ParsedRequest`
- `OrchestrationAgent -> InventoryAgent`
  - Input: `ParsedRequest`
  - Output: `InventoryResult`
- `OrchestrationAgent -> QuoteAgent`
  - Input: `ParsedRequest`, `InventoryResult`
  - Output: `QuoteResult`
- `OrchestrationAgent -> FulfillmentAgent`
  - Input: `ParsedRequest`, `InventoryResult`, `QuoteResult`
  - Output: `FulfillmentResult`
- `OrchestrationAgent -> User`
  - Input: all prior outputs plus report snapshot
  - Output: consolidated text response

## Framework Used

- Recommended framework selected and used: **pydantic-ai**.
- Worker agents use attached `pydantic_ai.Agent` objects for reasoning/response composition.
- Orchestration remains in `OrchestrationAgent` to manage delegation and output assembly.
