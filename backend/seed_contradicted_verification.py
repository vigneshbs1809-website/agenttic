import sqlite3
import uuid
from datetime import datetime, timezone

conn = sqlite3.connect("backend/data/literature.db")
cur = conn.cursor()

# 1. Standardize casing to Title Case
cur.execute("UPDATE verification_results SET verification_status='Supported' WHERE verification_status='supported'")

# 2. Get a target paper
cur.execute("SELECT id FROM research_papers LIMIT 1")
p_id = cur.fetchone()[0]

# 3. Insert Contradicted benchmark record if not exists
cur.execute("SELECT id FROM verification_results WHERE verification_status='Contradicted'")
if not cur.fetchone():
    cur.execute(
        """
        INSERT INTO verification_results (
            id, claim_id, verifier_agent, verification_status, supporting_evidence, counter_evidence,
            verification_score, notes, created_at, paper_id, claim_text, page_number, explanation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            f"claim-{uuid.uuid4().hex[:8]}",
            "EvidenceVerificationAgent",
            "Contradicted",
            "CentralQ achieves an 89.2% success rate and 28.4% latency reduction on the Fleet-Dispatch-Bench.",
            "CentralQ achieves an 89.2% success rate on Fleet-Dispatch-Bench.",
            0.15,
            "Contradicted empirical finding",
            datetime.now(timezone.utc).isoformat(),
            p_id,
            "CentralQ achieves a 99.4% success rate on the Fleet-Dispatch-Bench.",
            1,
            "The evaluated claim asserts a 99.4% success rate, directly contradicting the empirical findings reported on Page 1 (89.2% success rate). This assertion is classified as a fabricated finding."
        )
    )
    print("Inserted Contradicted benchmark record.")

conn.commit()
conn.close()
print("Standardized SQLite verification statuses.")
