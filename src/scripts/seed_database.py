# src/scripts/seed_database.py
import os
import sys
import psycopg2
from pgvector.psycopg2 import register_vector
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Fix the path so we can import the dataset
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dataset.orqestra_50 import train_set

load_dotenv()

# ==========================================
# 1. INITIALIZATION
# ==========================================
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Standard Docker PostgreSQL connection string
DB_URL = "postgresql://orqestra_admin:supersecretpassword@localhost:5432/orqestra"

def get_embedding(text):
    """Convert text into a 1536-dimensional float array using OpenAI."""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# ==========================================
# 2. DATABASE SETUP
# ==========================================
print("🔌 Connecting to PostgreSQL...")
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

print("📦 Enabling pgvector extension...")
cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
conn.commit()

# Register the vector type with psycopg2
register_vector(conn)

print("🏗️ Creating claims table...")
cur.execute("""
    DROP TABLE IF EXISTS enterprise_claims;
    CREATE TABLE enterprise_claims (
        id SERIAL PRIMARY KEY,
        system_name VARCHAR(255),
        claim_text TEXT,
        domain VARCHAR(50),
        embedding vector(1536)
    );
""")
conn.commit()

# ==========================================
# 3. SEEDING THE DATA
# ==========================================
print("🌱 Embedding and loading Orqestra 50 dataset...")

# We will just insert Claim A from all 50 examples to act as our "existing" database
for i, example in enumerate(train_set):
    claim_text = example.claim_a
    
    # Generate the vector math for the claim
    emb = get_embedding(claim_text)
    
    # Insert it into Postgres
    cur.execute(
        "INSERT INTO enterprise_claims (system_name, claim_text, domain, embedding) VALUES (%s, %s, %s, %s)",
        ("LegacySystem_A", claim_text, "MixedDomain", emb)
    )
    
    if (i + 1) % 10 == 0:
        print(f"   Inserted {i + 1}/50 claims...")

conn.commit()
cur.close()
conn.close()

print("✅ Database successfully seeded! pgvector is ready for similarity searches.")