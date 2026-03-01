import pandas as pd
import numpy as np
import os
import time
import dotenv
import ast
import re
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import Dict, List, Union, Optional
from sqlalchemy import create_engine, Engine

try:
    from pydantic_ai import Agent
    PYDANTIC_AI_AVAILABLE = True
except Exception:
    Agent = None
    PYDANTIC_AI_AVAILABLE = False

# Create an SQLite database
db_engine = create_engine("sqlite:///munder_difflin.db")

# List containing the different kinds of papers 
paper_supplies = [
    # Paper Types (priced per sheet unless specified)
    {"item_name": "A4 paper",                         "category": "paper",        "unit_price": 0.05},
    {"item_name": "Letter-sized paper",              "category": "paper",        "unit_price": 0.06},
    {"item_name": "Cardstock",                        "category": "paper",        "unit_price": 0.15},
    {"item_name": "Colored paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Glossy paper",                     "category": "paper",        "unit_price": 0.20},
    {"item_name": "Matte paper",                      "category": "paper",        "unit_price": 0.18},
    {"item_name": "Recycled paper",                   "category": "paper",        "unit_price": 0.08},
    {"item_name": "Eco-friendly paper",               "category": "paper",        "unit_price": 0.12},
    {"item_name": "Poster paper",                     "category": "paper",        "unit_price": 0.25},
    {"item_name": "Banner paper",                     "category": "paper",        "unit_price": 0.30},
    {"item_name": "Kraft paper",                      "category": "paper",        "unit_price": 0.10},
    {"item_name": "Construction paper",               "category": "paper",        "unit_price": 0.07},
    {"item_name": "Wrapping paper",                   "category": "paper",        "unit_price": 0.15},
    {"item_name": "Glitter paper",                    "category": "paper",        "unit_price": 0.22},
    {"item_name": "Decorative paper",                 "category": "paper",        "unit_price": 0.18},
    {"item_name": "Letterhead paper",                 "category": "paper",        "unit_price": 0.12},
    {"item_name": "Legal-size paper",                 "category": "paper",        "unit_price": 0.08},
    {"item_name": "Crepe paper",                      "category": "paper",        "unit_price": 0.05},
    {"item_name": "Photo paper",                      "category": "paper",        "unit_price": 0.25},
    {"item_name": "Uncoated paper",                   "category": "paper",        "unit_price": 0.06},
    {"item_name": "Butcher paper",                    "category": "paper",        "unit_price": 0.10},
    {"item_name": "Heavyweight paper",                "category": "paper",        "unit_price": 0.20},
    {"item_name": "Standard copy paper",              "category": "paper",        "unit_price": 0.04},
    {"item_name": "Bright-colored paper",             "category": "paper",        "unit_price": 0.12},
    {"item_name": "Patterned paper",                  "category": "paper",        "unit_price": 0.15},

    # Product Types (priced per unit)
    {"item_name": "Paper plates",                     "category": "product",      "unit_price": 0.10},  # per plate
    {"item_name": "Paper cups",                       "category": "product",      "unit_price": 0.08},  # per cup
    {"item_name": "Paper napkins",                    "category": "product",      "unit_price": 0.02},  # per napkin
    {"item_name": "Disposable cups",                  "category": "product",      "unit_price": 0.10},  # per cup
    {"item_name": "Table covers",                     "category": "product",      "unit_price": 1.50},  # per cover
    {"item_name": "Envelopes",                        "category": "product",      "unit_price": 0.05},  # per envelope
    {"item_name": "Sticky notes",                     "category": "product",      "unit_price": 0.03},  # per sheet
    {"item_name": "Notepads",                         "category": "product",      "unit_price": 2.00},  # per pad
    {"item_name": "Invitation cards",                 "category": "product",      "unit_price": 0.50},  # per card
    {"item_name": "Flyers",                           "category": "product",      "unit_price": 0.15},  # per flyer
    {"item_name": "Party streamers",                  "category": "product",      "unit_price": 0.05},  # per roll
    {"item_name": "Decorative adhesive tape (washi tape)", "category": "product", "unit_price": 0.20},  # per roll
    {"item_name": "Paper party bags",                 "category": "product",      "unit_price": 0.25},  # per bag
    {"item_name": "Name tags with lanyards",          "category": "product",      "unit_price": 0.75},  # per tag
    {"item_name": "Presentation folders",             "category": "product",      "unit_price": 0.50},  # per folder

    # Large-format items (priced per unit)
    {"item_name": "Large poster paper (24x36 inches)", "category": "large_format", "unit_price": 1.00},
    {"item_name": "Rolls of banner paper (36-inch width)", "category": "large_format", "unit_price": 2.50},

    # Specialty papers
    {"item_name": "100 lb cover stock",               "category": "specialty",    "unit_price": 0.50},
    {"item_name": "80 lb text paper",                 "category": "specialty",    "unit_price": 0.40},
    {"item_name": "250 gsm cardstock",                "category": "specialty",    "unit_price": 0.30},
    {"item_name": "220 gsm poster paper",             "category": "specialty",    "unit_price": 0.35},
]

# Given below are some utility functions you can use to implement your multi-agent system

def generate_sample_inventory(paper_supplies: list, coverage: float = 0.4, seed: int = 137) -> pd.DataFrame:
    """
    Generate inventory for exactly a specified percentage of items from the full paper supply list.

    This function randomly selects exactly `coverage` × N items from the `paper_supplies` list,
    and assigns each selected item:
    - a random stock quantity between 200 and 800,
    - a minimum stock level between 50 and 150.

    The random seed ensures reproducibility of selection and stock levels.

    Args:
        paper_supplies (list): A list of dictionaries, each representing a paper item with
                               keys 'item_name', 'category', and 'unit_price'.
        coverage (float, optional): Fraction of items to include in the inventory (default is 0.4, or 40%).
        seed (int, optional): Random seed for reproducibility (default is 137).

    Returns:
        pd.DataFrame: A DataFrame with the selected items and assigned inventory values, including:
                      - item_name
                      - category
                      - unit_price
                      - current_stock
                      - min_stock_level
    """
    # Ensure reproducible random output
    np.random.seed(seed)

    # Calculate number of items to include based on coverage
    num_items = int(len(paper_supplies) * coverage)

    # Randomly select item indices without replacement
    selected_indices = np.random.choice(
        range(len(paper_supplies)),
        size=num_items,
        replace=False
    )

    # Extract selected items from paper_supplies list
    selected_items = [paper_supplies[i] for i in selected_indices]

    # Construct inventory records
    inventory = []
    for item in selected_items:
        inventory.append({
            "item_name": item["item_name"],
            "category": item["category"],
            "unit_price": item["unit_price"],
            "current_stock": np.random.randint(200, 800),  # Realistic stock range
            "min_stock_level": np.random.randint(50, 150)  # Reasonable threshold for reordering
        })

    # Return inventory as a pandas DataFrame
    return pd.DataFrame(inventory)

def init_database(db_engine: Engine, seed: int = 137) -> Engine:    
    """
    Set up the Munder Difflin database with all required tables and initial records.

    This function performs the following tasks:
    - Creates the 'transactions' table for logging stock orders and sales
    - Loads customer inquiries from 'quote_requests.csv' into a 'quote_requests' table
    - Loads previous quotes from 'quotes.csv' into a 'quotes' table, extracting useful metadata
    - Generates a random subset of paper inventory using `generate_sample_inventory`
    - Inserts initial financial records including available cash and starting stock levels

    Args:
        db_engine (Engine): A SQLAlchemy engine connected to the SQLite database.
        seed (int, optional): A random seed used to control reproducibility of inventory stock levels.
                              Default is 137.

    Returns:
        Engine: The same SQLAlchemy engine, after initializing all necessary tables and records.

    Raises:
        Exception: If an error occurs during setup, the exception is printed and raised.
    """
    try:
        # ----------------------------
        # 1. Create an empty 'transactions' table schema
        # ----------------------------
        transactions_schema = pd.DataFrame({
            "id": [],
            "item_name": [],
            "transaction_type": [],  # 'stock_orders' or 'sales'
            "units": [],             # Quantity involved
            "price": [],             # Total price for the transaction
            "transaction_date": [],  # ISO-formatted date
        })
        transactions_schema.to_sql("transactions", db_engine, if_exists="replace", index=False)

        # Set a consistent starting date
        initial_date = datetime(2025, 1, 1).isoformat()

        # ----------------------------
        # 2. Load and initialize 'quote_requests' table
        # ----------------------------
        quote_requests_df = pd.read_csv("quote_requests.csv")
        quote_requests_df["id"] = range(1, len(quote_requests_df) + 1)
        quote_requests_df.to_sql("quote_requests", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 3. Load and transform 'quotes' table
        # ----------------------------
        quotes_df = pd.read_csv("quotes.csv")
        quotes_df["request_id"] = range(1, len(quotes_df) + 1)
        quotes_df["order_date"] = initial_date

        # Unpack metadata fields (job_type, order_size, event_type) if present
        if "request_metadata" in quotes_df.columns:
            quotes_df["request_metadata"] = quotes_df["request_metadata"].apply(
                lambda x: ast.literal_eval(x) if isinstance(x, str) else x
            )
            quotes_df["job_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("job_type", ""))
            quotes_df["order_size"] = quotes_df["request_metadata"].apply(lambda x: x.get("order_size", ""))
            quotes_df["event_type"] = quotes_df["request_metadata"].apply(lambda x: x.get("event_type", ""))

        # Retain only relevant columns
        quotes_df = quotes_df[[
            "request_id",
            "total_amount",
            "quote_explanation",
            "order_date",
            "job_type",
            "order_size",
            "event_type"
        ]]
        quotes_df.to_sql("quotes", db_engine, if_exists="replace", index=False)

        # ----------------------------
        # 4. Generate inventory and seed stock
        # ----------------------------
        inventory_df = generate_sample_inventory(paper_supplies, seed=seed)

        # Seed initial transactions
        initial_transactions = []

        # Add a starting cash balance via a dummy sales transaction
        initial_transactions.append({
            "item_name": None,
            "transaction_type": "sales",
            "units": None,
            "price": 50000.0,
            "transaction_date": initial_date,
        })

        # Add one stock order transaction per inventory item
        for _, item in inventory_df.iterrows():
            initial_transactions.append({
                "item_name": item["item_name"],
                "transaction_type": "stock_orders",
                "units": item["current_stock"],
                "price": item["current_stock"] * item["unit_price"],
                "transaction_date": initial_date,
            })

        # Commit transactions to database
        pd.DataFrame(initial_transactions).to_sql("transactions", db_engine, if_exists="append", index=False)

        # Save the inventory reference table
        inventory_df.to_sql("inventory", db_engine, if_exists="replace", index=False)

        return db_engine

    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def create_transaction(
    item_name: str,
    transaction_type: str,
    quantity: int,
    price: float,
    date: Union[str, datetime],
) -> int:
    """
    This function records a transaction of type 'stock_orders' or 'sales' with a specified
    item name, quantity, total price, and transaction date into the 'transactions' table of the database.

    Args:
        item_name (str): The name of the item involved in the transaction.
        transaction_type (str): Either 'stock_orders' or 'sales'.
        quantity (int): Number of units involved in the transaction.
        price (float): Total price of the transaction.
        date (str or datetime): Date of the transaction in ISO 8601 format.

    Returns:
        int: The ID of the newly inserted transaction.

    Raises:
        ValueError: If `transaction_type` is not 'stock_orders' or 'sales'.
        Exception: For other database or execution errors.
    """
    try:
        # Convert datetime to ISO string if necessary
        date_str = date.isoformat() if isinstance(date, datetime) else date

        # Validate transaction type
        if transaction_type not in {"stock_orders", "sales"}:
            raise ValueError("Transaction type must be 'stock_orders' or 'sales'")

        # Prepare transaction record as a single-row DataFrame
        transaction = pd.DataFrame([{
            "item_name": item_name,
            "transaction_type": transaction_type,
            "units": quantity,
            "price": price,
            "transaction_date": date_str,
        }])

        # Insert the record into the database
        transaction.to_sql("transactions", db_engine, if_exists="append", index=False)

        # Fetch and return the ID of the inserted row
        result = pd.read_sql("SELECT last_insert_rowid() as id", db_engine)
        return int(result.iloc[0]["id"])

    except Exception as e:
        print(f"Error creating transaction: {e}")
        raise

def get_all_inventory(as_of_date: str) -> Dict[str, int]:
    """
    Retrieve a snapshot of available inventory as of a specific date.

    This function calculates the net quantity of each item by summing 
    all stock orders and subtracting all sales up to and including the given date.

    Only items with positive stock are included in the result.

    Args:
        as_of_date (str): ISO-formatted date string (YYYY-MM-DD) representing the inventory cutoff.

    Returns:
        Dict[str, int]: A dictionary mapping item names to their current stock levels.
    """
    # SQL query to compute stock levels per item as of the given date
    query = """
        SELECT
            item_name,
            SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END) as stock
        FROM transactions
        WHERE item_name IS NOT NULL
        AND transaction_date <= :as_of_date
        GROUP BY item_name
        HAVING stock > 0
    """

    # Execute the query with the date parameter
    result = pd.read_sql(query, db_engine, params={"as_of_date": as_of_date})

    # Convert the result into a dictionary {item_name: stock}
    return dict(zip(result["item_name"], result["stock"]))

def get_stock_level(item_name: str, as_of_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Retrieve the stock level of a specific item as of a given date.

    This function calculates the net stock by summing all 'stock_orders' and 
    subtracting all 'sales' transactions for the specified item up to the given date.

    Args:
        item_name (str): The name of the item to look up.
        as_of_date (str or datetime): The cutoff date (inclusive) for calculating stock.

    Returns:
        pd.DataFrame: A single-row DataFrame with columns 'item_name' and 'current_stock'.
    """
    # Convert date to ISO string format if it's a datetime object
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # SQL query to compute net stock level for the item
    stock_query = """
        SELECT
            item_name,
            COALESCE(SUM(CASE
                WHEN transaction_type = 'stock_orders' THEN units
                WHEN transaction_type = 'sales' THEN -units
                ELSE 0
            END), 0) AS current_stock
        FROM transactions
        WHERE item_name = :item_name
        AND transaction_date <= :as_of_date
    """

    # Execute query and return result as a DataFrame
    return pd.read_sql(
        stock_query,
        db_engine,
        params={"item_name": item_name, "as_of_date": as_of_date},
    )

def get_supplier_delivery_date(input_date_str: str, quantity: int) -> str:
    """
    Estimate the supplier delivery date based on the requested order quantity and a starting date.

    Delivery lead time increases with order size:
        - ≤10 units: same day
        - 11–100 units: 1 day
        - 101–1000 units: 4 days
        - >1000 units: 7 days

    Args:
        input_date_str (str): The starting date in ISO format (YYYY-MM-DD).
        quantity (int): The number of units in the order.

    Returns:
        str: Estimated delivery date in ISO format (YYYY-MM-DD).
    """
    # Debug log (comment out in production if needed)
    print(f"FUNC (get_supplier_delivery_date): Calculating for qty {quantity} from date string '{input_date_str}'")

    # Attempt to parse the input date
    try:
        input_date_dt = datetime.fromisoformat(input_date_str.split("T")[0])
    except (ValueError, TypeError):
        # Fallback to current date on format error
        print(f"WARN (get_supplier_delivery_date): Invalid date format '{input_date_str}', using today as base.")
        input_date_dt = datetime.now()

    # Determine delivery delay based on quantity
    if quantity <= 10:
        days = 0
    elif quantity <= 100:
        days = 1
    elif quantity <= 1000:
        days = 4
    else:
        days = 7

    # Add delivery days to the starting date
    delivery_date_dt = input_date_dt + timedelta(days=days)

    # Return formatted delivery date
    return delivery_date_dt.strftime("%Y-%m-%d")

def get_cash_balance(as_of_date: Union[str, datetime]) -> float:
    """
    Calculate the current cash balance as of a specified date.

    The balance is computed by subtracting total stock purchase costs ('stock_orders')
    from total revenue ('sales') recorded in the transactions table up to the given date.

    Args:
        as_of_date (str or datetime): The cutoff date (inclusive) in ISO format or as a datetime object.

    Returns:
        float: Net cash balance as of the given date. Returns 0.0 if no transactions exist or an error occurs.
    """
    try:
        # Convert date to ISO format if it's a datetime object
        if isinstance(as_of_date, datetime):
            as_of_date = as_of_date.isoformat()

        # Query all transactions on or before the specified date
        transactions = pd.read_sql(
            "SELECT * FROM transactions WHERE transaction_date <= :as_of_date",
            db_engine,
            params={"as_of_date": as_of_date},
        )

        # Compute the difference between sales and stock purchases
        if not transactions.empty:
            total_sales = transactions.loc[transactions["transaction_type"] == "sales", "price"].sum()
            total_purchases = transactions.loc[transactions["transaction_type"] == "stock_orders", "price"].sum()
            return float(total_sales - total_purchases)

        return 0.0

    except Exception as e:
        print(f"Error getting cash balance: {e}")
        return 0.0


def generate_financial_report(as_of_date: Union[str, datetime]) -> Dict:
    """
    Generate a complete financial report for the company as of a specific date.

    This includes:
    - Cash balance
    - Inventory valuation
    - Combined asset total
    - Itemized inventory breakdown
    - Top 5 best-selling products

    Args:
        as_of_date (str or datetime): The date (inclusive) for which to generate the report.

    Returns:
        Dict: A dictionary containing the financial report fields:
            - 'as_of_date': The date of the report
            - 'cash_balance': Total cash available
            - 'inventory_value': Total value of inventory
            - 'total_assets': Combined cash and inventory value
            - 'inventory_summary': List of items with stock and valuation details
            - 'top_selling_products': List of top 5 products by revenue
    """
    # Normalize date input
    if isinstance(as_of_date, datetime):
        as_of_date = as_of_date.isoformat()

    # Get current cash balance
    cash = get_cash_balance(as_of_date)

    # Get current inventory snapshot
    inventory_df = pd.read_sql("SELECT * FROM inventory", db_engine)
    inventory_value = 0.0
    inventory_summary = []

    # Compute total inventory value and summary by item
    for _, item in inventory_df.iterrows():
        stock_info = get_stock_level(item["item_name"], as_of_date)
        stock = stock_info["current_stock"].iloc[0]
        item_value = stock * item["unit_price"]
        inventory_value += item_value

        inventory_summary.append({
            "item_name": item["item_name"],
            "stock": stock,
            "unit_price": item["unit_price"],
            "value": item_value,
        })

    # Identify top-selling products by revenue
    top_sales_query = """
        SELECT item_name, SUM(units) as total_units, SUM(price) as total_revenue
        FROM transactions
        WHERE transaction_type = 'sales' AND transaction_date <= :date
        GROUP BY item_name
        ORDER BY total_revenue DESC
        LIMIT 5
    """
    top_sales = pd.read_sql(top_sales_query, db_engine, params={"date": as_of_date})
    top_selling_products = top_sales.to_dict(orient="records")

    return {
        "as_of_date": as_of_date,
        "cash_balance": cash,
        "inventory_value": inventory_value,
        "total_assets": cash + inventory_value,
        "inventory_summary": inventory_summary,
        "top_selling_products": top_selling_products,
    }


def search_quote_history(search_terms: List[str], limit: int = 5) -> List[Dict]:
    """
    Retrieve a list of historical quotes that match any of the provided search terms.

    The function searches both the original customer request (from `quote_requests`) and
    the explanation for the quote (from `quotes`) for each keyword. Results are sorted by
    most recent order date and limited by the `limit` parameter.

    Args:
        search_terms (List[str]): List of terms to match against customer requests and explanations.
        limit (int, optional): Maximum number of quote records to return. Default is 5.

    Returns:
        List[Dict]: A list of matching quotes, each represented as a dictionary with fields:
            - original_request
            - total_amount
            - quote_explanation
            - job_type
            - order_size
            - event_type
            - order_date
    """
    conditions = []
    params = {}

    # Build SQL WHERE clause using LIKE filters for each search term
    for i, term in enumerate(search_terms):
        param_name = f"term_{i}"
        conditions.append(
            f"(LOWER(qr.response) LIKE :{param_name} OR "
            f"LOWER(q.quote_explanation) LIKE :{param_name})"
        )
        params[param_name] = f"%{term.lower()}%"

    # Combine conditions; fallback to always-true if no terms provided
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Final SQL query to join quotes with quote_requests
    query = f"""
        SELECT
            qr.response AS original_request,
            q.total_amount,
            q.quote_explanation,
            q.job_type,
            q.order_size,
            q.event_type,
            q.order_date
        FROM quotes q
        JOIN quote_requests qr ON q.request_id = qr.id
        WHERE {where_clause}
        ORDER BY q.order_date DESC
        LIMIT {limit}
    """

    # Execute parameterized query
    with db_engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]

########################
########################
########################
# YOUR MULTI AGENT STARTS HERE
########################
########################
########################

# This project can run without external LLM APIs by using deterministic, text-driven agents.
# Agents: parsing, inventory/reordering, quoting, fulfillment, and orchestration.

dotenv.load_dotenv()


def _configure_model_env() -> str:
    """
    Force Vocareum OpenAI-compatible endpoint/key wiring for pydantic-ai and
    return the model identifier to use.
    """
    # Prefer Vocareum-provided key when present.
    if os.getenv("UDACITY_OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = os.getenv("UDACITY_OPENAI_API_KEY")

    # Always route through Vocareum proxy for this project.
    os.environ["OPENAI_BASE_URL"] = "https://openai.vocareum.com/v1"

    return os.getenv("PAPER_AGENT_MODEL", "openai:gpt-4o-mini")


def _llm_enabled() -> bool:
    return PYDANTIC_AI_AVAILABLE and bool(os.getenv("OPENAI_API_KEY"))


def _safe_agent_run(agent: Optional["Agent"], prompt: str) -> str:
    if not agent:
        return ""
    try:
        result = agent.run_sync(prompt)
        return str(getattr(result, "data", ""))
    except Exception:
        return ""


_REQUEST_DATE_PATTERN = re.compile(r"Date of request:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)
_DELIVERY_DATE_PATTERN = re.compile(r"by\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})", re.IGNORECASE)
_ITEM_PATTERN = re.compile(
    r"(\d[\d,]*)\s*(sheets?|reams?|rolls?|boxes?|packets?|cups?|plates?|napkins?|"
    r"flyers?|posters?|tickets?|folders?|cards?)?\s*(?:of\s+)?"
    r"([A-Za-z0-9\-\(\)\"'/\s]+?)(?=(?:,|\.|\n|\band\b|$))",
    re.IGNORECASE,
)

_UNIT_MULTIPLIER = {
    "ream": 500,
    "reams": 500,
    "box": 100,
    "boxes": 100,
    "packet": 100,
    "packets": 100,
}

_ITEM_ALIASES = {
    "a4 paper": "A4 paper",
    "a4 glossy paper": "Glossy paper",
    "a3 glossy paper": "Glossy paper",
    "a4 matte paper": "Matte paper",
    "a3 matte paper": "Matte paper",
    "letter paper": "Letter-sized paper",
    "letter-sized paper": "Letter-sized paper",
    "printer paper": "Standard copy paper",
    "printing paper": "Standard copy paper",
    "white printer paper": "Standard copy paper",
    "standard printer paper": "Standard copy paper",
    "cardstock": "Cardstock",
    "heavy cardstock": "Cardstock",
    "colored cardstock": "Cardstock",
    "colored paper": "Colored paper",
    "construction paper": "Construction paper",
    "poster board": "Large poster paper (24x36 inches)",
    "poster boards": "Large poster paper (24x36 inches)",
    "poster paper": "Poster paper",
    "streamers": "Party streamers",
    "washi tape": "Decorative adhesive tape (washi tape)",
    "table napkins": "Paper napkins",
    "napkins": "Paper napkins",
    "paper cups": "Paper cups",
    "paper plates": "Paper plates",
    "cups": "Paper cups",
    "plates": "Paper plates",
    "flyers": "Flyers",
    "posters": "Large poster paper (24x36 inches)",
    "envelopes": "Envelopes",
}


def _normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _extract_request_date(request_text: str) -> str:
    match = _REQUEST_DATE_PATTERN.search(request_text)
    if match:
        return match.group(1)
    return datetime.now().strftime("%Y-%m-%d")


def _extract_delivery_date(request_text: str, request_date: str) -> str:
    match = _DELIVERY_DATE_PATTERN.search(request_text)
    if not match:
        return (datetime.fromisoformat(request_date) + timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        return datetime.strptime(match.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return (datetime.fromisoformat(request_date) + timedelta(days=7)).strftime("%Y-%m-%d")


def _load_price_catalog() -> Dict[str, float]:
    inventory_df = pd.read_sql("SELECT item_name, unit_price FROM inventory", db_engine)
    catalog = dict(zip(inventory_df["item_name"], inventory_df["unit_price"]))
    for item in paper_supplies:
        catalog.setdefault(item["item_name"], item["unit_price"])
    return catalog


def _resolve_item_name(raw_item: str, valid_items: List[str]) -> Optional[str]:
    normalized = _normalize_text(raw_item)
    if not normalized:
        return None

    if normalized in _ITEM_ALIASES:
        return _ITEM_ALIASES[normalized]

    for key, canonical in _ITEM_ALIASES.items():
        if key in normalized or normalized in key:
            return canonical

    normalized_to_actual = {_normalize_text(item): item for item in valid_items}
    if normalized in normalized_to_actual:
        return normalized_to_actual[normalized]

    best_item = None
    best_overlap = 0
    raw_tokens = set(normalized.split())
    for candidate in valid_items:
        candidate_tokens = set(_normalize_text(candidate).split())
        overlap = len(raw_tokens.intersection(candidate_tokens))
        if overlap > best_overlap:
            best_overlap = overlap
            best_item = candidate

    return best_item if best_overlap >= 1 else None


class RequestParsingAgent:
    def __init__(self, model_name: str):
        self.valid_items = [item["item_name"] for item in paper_supplies]
        self.tools = {
            "extract_request_date": _extract_request_date,
            "extract_delivery_date": _extract_delivery_date,
        }
        self.parser_llm = None
        if _llm_enabled():
            self.parser_llm = Agent(
                model_name,
                system_prompt=(
                    "You are a request parsing specialist for paper inventory/quotes. "
                    "Given a request, return one short line that states intent and any risky ambiguities."
                ),
            )

            @self.parser_llm.tool_plain
            def extract_request_date_tool(request_text: str) -> str:
                return self.tools["extract_request_date"](request_text)

            @self.parser_llm.tool_plain
            def extract_delivery_date_tool(request_text: str, request_date: str) -> str:
                return self.tools["extract_delivery_date"](request_text, request_date)

    def parse(self, request_text: str) -> Dict:
        request_date = self.tools["extract_request_date"](request_text)
        delivery_date = self.tools["extract_delivery_date"](request_text, request_date)

        job_match = re.search(r"Customer job:\s*([^;]+)", request_text, re.IGNORECASE)
        need_size_match = re.search(r"order size:\s*([^;]+)", request_text, re.IGNORECASE)
        event_match = re.search(r"event:\s*([^.;]+)", request_text, re.IGNORECASE)

        items = []
        unknown_items = []
        for qty_raw, unit_raw, item_raw in _ITEM_PATTERN.findall(request_text):
            quantity = int(qty_raw.replace(",", ""))
            unit = (unit_raw or "").lower().strip()
            multiplier = _UNIT_MULTIPLIER.get(unit, 1)
            resolved = _resolve_item_name(item_raw.strip(), self.valid_items)
            total_quantity = int(quantity * multiplier)

            if not resolved:
                unknown_items.append({"raw_item": item_raw.strip(), "quantity": total_quantity})
                continue

            items.append({"item_name": resolved, "quantity": total_quantity, "raw_item": item_raw.strip()})

        deduped = {}
        for entry in items:
            deduped[entry["item_name"]] = deduped.get(entry["item_name"], 0) + entry["quantity"]

        llm_hint = _safe_agent_run(
            self.parser_llm,
            f"Analyze this customer request for parsing concerns:\n{request_text}",
        )

        return {
            "request_text": request_text,
            "request_date": request_date,
            "delivery_date": delivery_date,
            "job": (job_match.group(1).strip() if job_match else "unknown"),
            "need_size": (need_size_match.group(1).strip() if need_size_match else "unknown"),
            "event": (event_match.group(1).strip() if event_match else "unknown"),
            "items": [{"item_name": k, "quantity": v} for k, v in deduped.items()],
            "unknown_items": unknown_items,
            "is_inventory_question": "inventory" in request_text.lower() or "stock" in request_text.lower(),
            "parser_hint": llm_hint,
        }


class InventoryAgent:
    def __init__(self, model_name: str):
        self.catalog = _load_price_catalog()
        self.tools = {
            "inventory_snapshot": lambda as_of_date: get_all_inventory(as_of_date),
            "stock_level": lambda item_name, as_of_date: int(
                get_stock_level(item_name, as_of_date)["current_stock"].iloc[0]
            ),
            "cash_balance": lambda as_of_date: float(get_cash_balance(as_of_date)),
            "supplier_eta": lambda input_date_str, quantity: get_supplier_delivery_date(input_date_str, quantity),
            "stock_order_transaction": lambda item_name, quantity, price, date: create_transaction(
                item_name=item_name,
                transaction_type="stock_orders",
                quantity=quantity,
                price=price,
                date=date,
            ),
        }
        self.inventory_llm = None
        if _llm_enabled():
            self.inventory_llm = Agent(
                model_name,
                system_prompt=(
                    "You are an inventory operations specialist. "
                    "Summarize stock risk and reorder implications in one concise sentence."
                ),
            )

            @self.inventory_llm.tool_plain
            def inventory_snapshot_tool(as_of_date: str) -> Dict[str, int]:
                return self.tools["inventory_snapshot"](as_of_date)

            @self.inventory_llm.tool_plain
            def stock_level_tool(item_name: str, as_of_date: str) -> int:
                return self.tools["stock_level"](item_name, as_of_date)

            @self.inventory_llm.tool_plain
            def cash_balance_tool(as_of_date: str) -> float:
                return self.tools["cash_balance"](as_of_date)

            @self.inventory_llm.tool_plain
            def supplier_eta_tool(input_date_str: str, quantity: int) -> str:
                return self.tools["supplier_eta"](input_date_str, quantity)

            @self.inventory_llm.tool_plain
            def stock_order_transaction_tool(item_name: str, quantity: int, price: float, date: str) -> int:
                return self.tools["stock_order_transaction"](item_name, quantity, price, date)

    def check_and_reorder(self, parsed_request: Dict) -> Dict:
        request_date = parsed_request["request_date"]
        cash_balance = self.tools["cash_balance"](request_date)
        inventory_df = pd.read_sql("SELECT item_name, min_stock_level FROM inventory", db_engine)
        min_stock = dict(zip(inventory_df["item_name"], inventory_df["min_stock_level"]))

        inventory_status = []
        reorder_actions = []
        total_reorder_cost = 0.0

        for line in parsed_request["items"]:
            item = line["item_name"]
            requested_qty = int(line["quantity"])
            current_stock = self.tools["stock_level"](item, request_date)

            shortage = max(0, requested_qty - current_stock)
            reorder_qty = 0
            reorder_eta = request_date

            if shortage > 0:
                target_buffer = max(min_stock.get(item, 100), int(requested_qty * 0.2))
                reorder_qty = shortage + target_buffer
                unit_price = self.catalog[item]
                reorder_cost = reorder_qty * unit_price

                if total_reorder_cost + reorder_cost > cash_balance * 0.6:
                    affordable_qty = int(max(0, (cash_balance * 0.6 - total_reorder_cost) / max(unit_price, 0.01)))
                    reorder_qty = max(shortage, affordable_qty)
                    reorder_cost = reorder_qty * unit_price

                if reorder_qty > 0:
                    reorder_eta = self.tools["supplier_eta"](request_date, reorder_qty)
                    self.tools["stock_order_transaction"](
                        item_name=item,
                        quantity=int(reorder_qty),
                        price=float(reorder_cost),
                        date=request_date,
                    )
                    total_reorder_cost += reorder_cost
                    reorder_actions.append(
                        {
                            "item_name": item,
                            "quantity": int(reorder_qty),
                            "cost": float(reorder_cost),
                            "eta": reorder_eta,
                        }
                    )

            inventory_status.append(
                {
                    "item_name": item,
                    "requested_qty": requested_qty,
                    "stock_before": current_stock,
                    "shortage": shortage,
                    "available_after_reorder": current_stock + reorder_qty,
                    "availability_date": reorder_eta if shortage > 0 else request_date,
                }
            )

        llm_summary = _safe_agent_run(
            self.inventory_llm,
            f"Request date: {request_date}\nInventory status: {inventory_status}\nReorders: {reorder_actions}",
        )

        return {
            "inventory_status": inventory_status,
            "reorder_actions": reorder_actions,
            "total_reorder_cost": total_reorder_cost,
            "inventory_summary": llm_summary,
        }

    def answer_inventory_question(self, parsed_request: Dict) -> str:
        snapshot = self.tools["inventory_snapshot"](parsed_request["request_date"])
        if not snapshot:
            return "Current inventory is empty."
        top_items = sorted(snapshot.items(), key=lambda kv: kv[1], reverse=True)[:10]
        lines = [f"- {name}: {qty} units" for name, qty in top_items]
        return "Current inventory snapshot (top 10):\n" + "\n".join(lines)


class QuoteAgent:
    def __init__(self, model_name: str):
        self.catalog = _load_price_catalog()
        self.tools = {
            "quote_history_search": lambda search_terms, limit=8: search_quote_history(search_terms, limit=limit),
        }
        self.quote_llm = None
        if _llm_enabled():
            self.quote_llm = Agent(
                model_name,
                system_prompt=(
                    "You are a paper quoting specialist. "
                    "Write a concise customer-facing explanation for the final quote."
                ),
            )

            @self.quote_llm.tool_plain
            def quote_history_search_tool(search_terms: List[str], limit: int = 8) -> List[Dict]:
                return self.tools["quote_history_search"](search_terms, limit=limit)

    def _estimate_history_adjustment(self, parsed_request: Dict, subtotal: float) -> float:
        terms = [parsed_request["job"], parsed_request["event"], parsed_request["need_size"]]
        terms.extend([line["item_name"].split()[0].lower() for line in parsed_request["items"][:3]])
        history = self.tools["quote_history_search"]([t for t in terms if t and t != "unknown"], limit=8)

        if not history or subtotal <= 0:
            return 0.0

        amounts = [float(row["total_amount"]) for row in history if row.get("total_amount") is not None]
        if not amounts:
            return 0.0

        avg_hist = float(np.mean(amounts))
        ratio = avg_hist / subtotal

        if ratio < 0.85:
            return 0.03
        if ratio > 1.15:
            return -0.02
        return 0.0

    def build_quote(self, parsed_request: Dict, inventory_result: Dict) -> Dict:
        line_items = []
        subtotal = 0.0
        total_units = 0

        for line in parsed_request["items"]:
            item = line["item_name"]
            qty = int(line["quantity"])
            unit_price = float(self.catalog.get(item, 0.1))
            margin_multiplier = 1.25
            quoted_unit_price = round(unit_price * margin_multiplier, 4)
            line_total = quoted_unit_price * qty

            line_items.append(
                {
                    "item_name": item,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "quoted_unit_price": quoted_unit_price,
                    "line_total": line_total,
                }
            )
            subtotal += line_total
            total_units += qty

        bulk_discount = 0.0
        if total_units >= 8000:
            bulk_discount = 0.12
        elif total_units >= 3000:
            bulk_discount = 0.08
        elif total_units >= 1000:
            bulk_discount = 0.05

        history_adjustment = self._estimate_history_adjustment(parsed_request, subtotal)
        final_discount = min(max(bulk_discount + history_adjustment, 0.0), 0.20)
        discount_amount = subtotal * final_discount
        total_amount = round(subtotal - discount_amount, 2)

        if subtotal > 0:
            factor = total_amount / subtotal
            for line in line_items:
                line["final_line_total"] = round(line["line_total"] * factor, 2)
        else:
            for line in line_items:
                line["final_line_total"] = 0.0

        summary = (
            f"Quoted subtotal ${subtotal:.2f}; bulk/history discount {final_discount * 100:.1f}% "
            f"-> final quote ${total_amount:.2f}."
        )

        llm_explanation = _safe_agent_run(
            self.quote_llm,
            (
                f"Items: {line_items}\nSubtotal: {subtotal:.2f}\n"
                f"Discount percent: {final_discount * 100:.2f}\nFinal total: {total_amount:.2f}\n"
                "Write a short, clear quote explanation."
            ),
        )

        return {
            "line_items": line_items,
            "subtotal": round(subtotal, 2),
            "discount_pct": round(final_discount, 4),
            "discount_amount": round(discount_amount, 2),
            "total_amount": total_amount,
            "summary": llm_explanation or summary,
        }


class FulfillmentAgent:
    def __init__(self, model_name: str):
        self.tools = {
            "sales_transaction": lambda item_name, quantity, price, date: create_transaction(
                item_name=item_name,
                transaction_type="sales",
                quantity=quantity,
                price=price,
                date=date,
            ),
        }
        self.fulfillment_llm = None
        if _llm_enabled():
            self.fulfillment_llm = Agent(
                model_name,
                system_prompt=(
                    "You are a fulfillment coordinator. "
                    "Write one concise customer status message for order confirmation or delay."
                ),
            )

            @self.fulfillment_llm.tool_plain
            def sales_transaction_tool(item_name: str, quantity: int, price: float, date: str) -> int:
                return self.tools["sales_transaction"](item_name, quantity, price, date)

    def finalize(self, parsed_request: Dict, inventory_result: Dict, quote_result: Dict) -> Dict:
        delivery_date = parsed_request["delivery_date"]
        request_date = parsed_request["request_date"]

        availability = {
            row["item_name"]: row["availability_date"]
            for row in inventory_result["inventory_status"]
        }

        can_fulfill = True
        blockers = []
        for line in quote_result["line_items"]:
            item = line["item_name"]
            available_date = availability.get(item, request_date)
            if available_date > delivery_date:
                can_fulfill = False
                blockers.append(f"{item} available on {available_date}")

        if not quote_result["line_items"]:
            return {
                "status": "no_valid_items",
                "message": "No recognized catalog items were found in this request.",
                "sale_total": 0.0,
            }

        if can_fulfill:
            transaction_date = delivery_date
            for line in quote_result["line_items"]:
                self.tools["sales_transaction"](
                    item_name=line["item_name"],
                    quantity=int(line["quantity"]),
                    price=float(line["final_line_total"]),
                    date=transaction_date,
                )
            confirmed_msg = f"Order confirmed for delivery by {delivery_date}."
            llm_message = _safe_agent_run(
                self.fulfillment_llm,
                f"Create customer confirmation message for delivery date {delivery_date}.",
            )
            return {
                "status": "confirmed",
                "message": llm_message or confirmed_msg,
                "sale_total": quote_result["total_amount"],
            }

        delay_msg = "Cannot meet requested delivery date. " + "; ".join(blockers)
        llm_delay = _safe_agent_run(
            self.fulfillment_llm,
            f"Create customer delay message. Details: {delay_msg}",
        )
        return {
            "status": "pending_restock",
            "message": llm_delay or delay_msg,
            "sale_total": 0.0,
        }


class OrchestrationAgent:
    def __init__(self):
        self.model_name = _configure_model_env()
        self.parser = RequestParsingAgent(self.model_name)
        self.inventory_agent = InventoryAgent(self.model_name)
        self.quote_agent = QuoteAgent(self.model_name)
        self.fulfillment_agent = FulfillmentAgent(self.model_name)
        self.tools = {
            "financial_state_view": lambda as_of_date: generate_financial_report(as_of_date),
        }
        self.orchestrator_llm = None
        if _llm_enabled():
            self.orchestrator_llm = Agent(
                self.model_name,
                system_prompt=(
                    "You are the lead sales operations orchestrator for a paper company. "
                    "Return one concise final customer response that combines quote, fulfillment, "
                    "and any reorder or unknown-item notes."
                ),
            )

            @self.orchestrator_llm.tool_plain
            def financial_state_view_tool(as_of_date: str) -> Dict:
                return self.tools["financial_state_view"](as_of_date)

    def handle_request(self, request_text: str) -> str:
        parsed = self.parser.parse(request_text)

        if parsed["is_inventory_question"] and not parsed["items"]:
            return self.inventory_agent.answer_inventory_question(parsed)

        inventory_result = self.inventory_agent.check_and_reorder(parsed)
        quote_result = self.quote_agent.build_quote(parsed, inventory_result)
        fulfillment_result = self.fulfillment_agent.finalize(parsed, inventory_result, quote_result)

        reorder_note = ""
        if inventory_result["reorder_actions"]:
            parts = [
                f"{r['item_name']} x{r['quantity']} (ETA {r['eta']})"
                for r in inventory_result["reorder_actions"]
            ]
            reorder_note = " Reordered: " + ", ".join(parts) + "."

        unknown_note = ""
        if parsed["unknown_items"]:
            raw_unknown = ", ".join({item["raw_item"] for item in parsed["unknown_items"]})
            unknown_note = f" Unrecognized items skipped: {raw_unknown}."

        deterministic_message = (
            f"{quote_result['summary']} {fulfillment_result['message']}"
            f"{reorder_note}{unknown_note}"
        )
        llm_message = _safe_agent_run(
            self.orchestrator_llm,
            (
                f"Parsed metadata: job={parsed['job']}, event={parsed['event']}, size={parsed['need_size']}\n"
                f"Parser hint: {parsed.get('parser_hint', '')}\n"
                f"Inventory summary: {inventory_result.get('inventory_summary', '')}\n"
                f"Quote summary: {quote_result['summary']}\n"
                f"Fulfillment: {fulfillment_result['message']}\n"
                f"Reorder note: {reorder_note}\nUnknown note: {unknown_note}\n"
                "Compose the final customer response."
            ),
        )
        return llm_message or deterministic_message

    def get_financial_report(self, as_of_date: str) -> Dict:
        return self.tools["financial_state_view"](as_of_date)


# Run your test scenarios by writing them here. Make sure to keep track of them.

def run_test_scenarios():
    
    print("Initializing Database...")
    init_database(db_engine)
    try:
        quote_requests_sample = pd.read_csv("quote_requests_sample.csv")
        quote_requests_sample["request_date"] = pd.to_datetime(
            quote_requests_sample["request_date"], format="%m/%d/%y", errors="coerce"
        )
        quote_requests_sample.dropna(subset=["request_date"], inplace=True)
        quote_requests_sample = quote_requests_sample.sort_values("request_date")
    except Exception as e:
        print(f"FATAL: Error loading test data: {e}")
        return

    system = OrchestrationAgent()
    if _llm_enabled():
        print(
            f"Framework: pydantic-ai enabled ({system.model_name}) via "
            f"{os.getenv('OPENAI_BASE_URL', 'https://openai.vocareum.com/v1')}"
        )
    else:
        print("Framework: deterministic fallback (set OPENAI_API_KEY or UDACITY_OPENAI_API_KEY to enable pydantic-ai)")

    # Get initial state
    initial_date = quote_requests_sample["request_date"].min().strftime("%Y-%m-%d")
    report = system.get_financial_report(initial_date)
    current_cash = report["cash_balance"]
    current_inventory = report["inventory_value"]

    results = []
    for idx, row in quote_requests_sample.iterrows():
        request_date = row["request_date"].strftime("%Y-%m-%d")

        print(f"\n=== Request {idx+1} ===")
        print(f"Context: {row['job']} organizing {row['event']}")
        print(f"Request Date: {request_date}")
        print(f"Cash Balance: ${current_cash:.2f}")
        print(f"Inventory Value: ${current_inventory:.2f}")

        # Process request
        request_with_date = f"{row['request']} (Date of request: {request_date})"

        request_with_context = (
            f"Customer job: {row['job']}; order size: {row['need_size']}; event: {row['event']}. "
            f"Request: {request_with_date}"
        )
        response = system.handle_request(request_with_context)

        # Update state
        report = system.get_financial_report(request_date)
        current_cash = report["cash_balance"]
        current_inventory = report["inventory_value"]

        print(f"Response: {response}")
        print(f"Updated Cash: ${current_cash:.2f}")
        print(f"Updated Inventory: ${current_inventory:.2f}")

        results.append(
            {
                "request_id": idx + 1,
                "request_date": request_date,
                "cash_balance": current_cash,
                "inventory_value": current_inventory,
                "response": response,
            }
        )

        time.sleep(1)

    # Final report
    final_date = quote_requests_sample["request_date"].max().strftime("%Y-%m-%d")
    final_report = system.get_financial_report(final_date)
    print("\n===== FINAL FINANCIAL REPORT =====")
    print(f"Final Cash: ${final_report['cash_balance']:.2f}")
    print(f"Final Inventory: ${final_report['inventory_value']:.2f}")

    # Save results
    pd.DataFrame(results).to_csv("test_results.csv", index=False)
    return results


if __name__ == "__main__":
    results = run_test_scenarios()
