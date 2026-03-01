# Implementation Mermaid Diagram

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
