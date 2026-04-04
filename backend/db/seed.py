"""
Seed the database with 50 mock transactions for demo purposes.
Run once at startup if DB is empty.
"""
import random
from sqlalchemy.orm import Session
from features.transactions.models import Transaction

VENDORS = [
    ("Amazon Web Services", 0.9), ("Microsoft Azure", 0.9), ("Google Cloud", 0.9),
    ("BT Business", 0.85), ("Virgin Media", 0.85), ("Royal Mail", 0.8),
    ("Staples Office", 0.75), ("Office Depot", 0.75), ("Tesco Business", 0.7),
    ("Travis Perkins", 0.7), ("Screwfix", 0.65), ("B&Q Commercial", 0.65),
    ("Unknown Vendor 1234", 0.1), ("Cash Payment", 0.1), ("Misc Supplier", 0.2),
    ("Unverified Ltd", 0.15), ("Overseas Transfer", 0.2), ("XYZ Consulting", 0.3),
    ("Freelancer Invoice", 0.35), ("International Corp", 0.25),
]

CATEGORIES = [
    "Software & Subscriptions", "Utilities", "Office Supplies",
    "Travel & Transport", "Professional Services", "Equipment",
    "Marketing & Advertising", "Payroll", "General Expenses",
]

DESCRIPTIONS = [
    "Monthly subscription", "Annual licence", "Office supplies order",
    "Business travel expenses", "Consulting fee", "Equipment purchase",
    "Utility bill payment", "Marketing campaign", "Staff training",
    "Cloud hosting invoice", "Maintenance contract", "Legal fees",
]


def seed(db: Session) -> None:
    """Add 50 mock transactions if the table is empty."""
    existing = db.query(Transaction).count()
    if existing > 0:
        return

    random.seed(42)
    transactions = []

    for i in range(50):
        vendor, trust = random.choice(VENDORS)
        # ~15% suspicious transactions
        if random.random() < 0.15:
            amount = random.uniform(5000, 12000)
            vendor, trust = random.choice(VENDORS[-7:])  # untrusted vendors
        else:
            amount = random.uniform(50, 3000)

        transactions.append(Transaction(
            vendor=vendor,
            amount=round(amount, 2),
            description=random.choice(DESCRIPTIONS),
            category=random.choice(CATEGORIES),
            vendor_trust=trust,
            frequency_score=random.uniform(0.2, 0.9),
            is_processed=False,
            is_anomaly=False,
        ))

    db.add_all(transactions)
    db.commit()
    print(f"✅ Seeded {len(transactions)} transactions")
