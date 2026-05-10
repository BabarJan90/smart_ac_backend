"""
SmartAC - Agentic Product Recommendations
Uses LangChain + LangGraph ReAct agent to autonomously
decide which products to recommend based on conversation context.
No hardcoded logic - Claude decides everything.
"""
import hashlib
import time
import requests
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from core.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS_AGENT, PRODUCT_API_URL, CACHE_TTL_SECONDS

# ── Soft Cache ─────────────────────────────────────────────────────────────
_cache: dict = {}


def _cache_key(conversation: str) -> str:
    return hashlib.md5(conversation.strip().lower().encode()).hexdigest()


def _get_cache(key: str):
    entry = _cache.get(key)
    if not entry:
        return None
    if time.time() > entry["expires_at"]:
        del _cache[key]
        return None
    return entry["products"]


def _set_cache(key: str, products: list):
    _cache[key] = {
        "products": products,
        "expires_at": time.time() + CACHE_TTL_SECONDS,
    }


# ── FakeStore Product Fetcher ──────────────────────────────────────────────
def _fetch_all_products() -> list:
    try:
        response = requests.get(PRODUCT_API_URL, timeout=10)
        data = response.json()
        products = data.get("products", data)
        return [
            {
                "id": p["id"],
                "title": p["title"],
                "price": p["price"],
                "category": p.get("category", "general"),
                "image": p.get("thumbnail", ""),
                "description": p.get("description", ""),
                "rating": p.get("rating", 0),
            }
            for p in products
        ]
    except Exception:
        return []


# ── Agentic Product Recommendation ────────────────────────────────────────
def get_product_recommendations(conversation: str) -> dict:
    """
    Fully agentic product recommendations.
    Claude autonomously decides which products to recommend
    based on the conversation - no hardcoded logic.
    """
    started_at = datetime.now(timezone.utc)

    # ── Check cache first ──────────────────────────────────────────────────
    cache_key = _cache_key(conversation)
    cached = _get_cache(cache_key)
    if cached:
        return {
            "source": "cache",
            "products": cached,
            "conversation_summary": "Returned from cache",
            "duration_seconds": 0,
        }

    # ── Fetch all products once ────────────────────────────────────────────
    all_products = _fetch_all_products()
    recommendations = []

    # ── Define tools ───────────────────────────────────────────────────────

    @tool
    def search_products(query: str) -> str:
        """Search for products relevant to a topic or keyword.
        Use this to find products matching themes from the conversation.
        You can call this multiple times with different queries."""
        results = []
        query_lower = query.lower()
        for p in all_products:
            title_lower = p.get("title", "").lower()
            category_lower = p.get("category", "").lower()
            desc_lower = p.get("description", "").lower()
            if (query_lower in title_lower or
                query_lower in category_lower or
                any(word in title_lower or word in desc_lower
                    for word in query_lower.split())):
                results.append({
                    "id": p["id"],
                    "title": p["title"],
                    "price": p["price"],
                    "category": p["category"],
                    "image": p["image"],
                    "rating": p.get("rating", 0) if not isinstance(p.get("rating"), dict) else p.get("rating", {}).get("rate", 0),
                })
        if not results:
            # Return top rated if no match
            sorted_products = sorted(
                all_products,
                key=lambda x: x.get("rating", 0),
                reverse=True
            )[:3]
            results = [{
                "id": p["id"],
                "title": p["title"],
                "price": p["price"],
                "category": p["category"],
                "image": p["image"],
                "rating": p.get("rating", 0) if not isinstance(p.get("rating"), dict) else p.get("rating", {}).get("rate", 0),
            } for p in sorted_products]
        return str(results[:5])

    @tool
    def add_recommendation(
        product_id: int,
        title: str,
        price: float,
        category: str,
        image: str,
        reason: str,
        rating: float = 0.0,
    ) -> str:
        """Add a product to the final recommendations list.
        Always provide a clear reason why this product is relevant
        to the conversation context."""
        recommendations.append({
            "id": product_id,
            "title": title,
            "price": price,
            "category": category,
            "image": image,
            "reason": reason,
            "rating": rating,
        })
        return f"Added '{title}' to recommendations"

    @tool
    def get_categories() -> str:
        """Get all available product categories.
        Use this to understand what types of products are available."""
        categories = list(set(p.get("category", "") for p in all_products))
        return str(categories)

    # ── Build ReAct Agent ──────────────────────────────────────────────────
    tools = [search_products, add_recommendation, get_categories]

    llm = ChatAnthropic(
    model=ANTHROPIC_MODEL,
    max_tokens=ANTHROPIC_MAX_TOKENS_AGENT,
    api_key=ANTHROPIC_API_KEY,
)

    system_prompt = f"""You are an intelligent product recommendation agent for SmartAC.

    A user has just had the following conversation:
    "{conversation}"

    Your job is to recommend 3-5 relevant products based on the conversation context.

    Instructions:
    1. First understand what the conversation is about
    2. Use get_categories to see what product types are available
    3. Use search_products to find relevant products (call multiple times with different queries)
    4. Use add_recommendation to add the most relevant products with clear reasons
    5. Aim for 3-5 diverse, relevant recommendations

    Be creative in finding connections between the conversation and products.
    For example:
    - Financial/accounting conversation → office supplies, organisers, books
    - Tech conversation → electronics, gadgets
    - Health conversation → health & beauty products
    Always explain WHY each product is relevant to the conversation."""

    agent = create_react_agent(llm, tools, prompt=system_prompt)

    result = agent.invoke({
        "messages": [("human", f"Analyse this conversation and recommend relevant products: {conversation}")]
    })


    
    # ── Extract summary ────────────────────────────────────────────────────
    final_message = ""
    agent_steps = []
    
    for msg in result.get("messages", []):
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                agent_steps.append(f"Tool: {tc['name']} → {str(tc['args'])[:100]}")
        elif hasattr(msg, 'name') and msg.name:
            agent_steps.append(f"Result: {msg.name} → {str(msg.content)[:100]}")
        if hasattr(msg, 'content') and isinstance(msg.content, str) and msg.content:
            final_message = msg.content

    # ── Cache results ──────────────────────────────────────────────────────
    _set_cache(cache_key, recommendations)

    duration = round(
        (datetime.now(timezone.utc) - started_at).total_seconds(), 2
    )

    return {
        "source": "agent",
        "products": recommendations,
        "conversation_summary": final_message,
        "duration_seconds": duration,
        "agent_steps": agent_steps,
    }