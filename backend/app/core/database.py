import logging
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import settings
from backend.app.models.entities import Base

logger = logging.getLogger(__name__)

def get_db_file_path() -> Path:
    p = Path(settings.SQLITE_DB_PATH)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

DB_PATH = get_db_file_path()
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# Initialize SQLAlchemy Engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30.0},
    pool_pre_ping=True
)

# Configure SQLite for Windows 11 & Low RAM concurrency (WAL mode + Foreign Keys)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA cache_size=-8000;")  # 8 MB memory cache limit
    cursor.close()

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database sessions with automatic rollback and closure."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise e
    finally:
        db.close()

def init_db():
    """Initializes all normalized database tables and creates schema."""
    try:
        get_db_file_path()
        Base.metadata.create_all(bind=engine)

        # Run safe SQLite schema migrations for newly added model columns
        with engine.connect() as conn:
            # 1. research_papers migrations
            cursor = conn.execute(text("PRAGMA table_info(research_papers);"))
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "extracted_text_path" not in columns:
                conn.execute(text("ALTER TABLE research_papers ADD COLUMN extracted_text_path TEXT;"))
            if columns and "error_message" not in columns:
                conn.execute(text("ALTER TABLE research_papers ADD COLUMN error_message TEXT;"))

            # 2. paper_sections migrations
            cursor_sec = conn.execute(text("PRAGMA table_info(paper_sections);"))
            sec_columns = [row[1] for row in cursor_sec.fetchall()]
            if sec_columns and "page_number" not in sec_columns:
                conn.execute(text("ALTER TABLE paper_sections ADD COLUMN page_number INTEGER;"))

            # 3. paper_analyses migrations
            cursor_an = conn.execute(text("PRAGMA table_info(paper_analyses);"))
            an_columns = [row[1] for row in cursor_an.fetchall()]
            if an_columns and "structured_data" not in an_columns:
                conn.execute(text("ALTER TABLE paper_analyses ADD COLUMN structured_data TEXT;"))
            if an_columns and "report_markdown" not in an_columns:
                conn.execute(text("ALTER TABLE paper_analyses ADD COLUMN report_markdown TEXT;"))

            # 4. research_gaps migrations
            cursor_gap = conn.execute(text("PRAGMA table_info(research_gaps);"))
            gap_columns = [row[1] for row in cursor_gap.fetchall()]
            if gap_columns and "identification_method" not in gap_columns:
                conn.execute(text("ALTER TABLE research_gaps ADD COLUMN identification_method VARCHAR(50) DEFAULT 'implicit_system_inferred';"))
            if gap_columns and "confidence_score" not in gap_columns:
                conn.execute(text("ALTER TABLE research_gaps ADD COLUMN confidence_score FLOAT DEFAULT 0.5;"))
            if gap_columns and "confidence_justification" not in gap_columns:
                conn.execute(text("ALTER TABLE research_gaps ADD COLUMN confidence_justification TEXT;"))
            if gap_columns and "suggested_direction" not in gap_columns:
                conn.execute(text("ALTER TABLE research_gaps ADD COLUMN suggested_direction TEXT;"))
            if gap_columns and "counter_evidence" not in gap_columns:
                conn.execute(text("ALTER TABLE research_gaps ADD COLUMN counter_evidence TEXT;"))
            if gap_columns and "supporting_papers_count" not in gap_columns:
                conn.execute(text("ALTER TABLE research_gaps ADD COLUMN supporting_papers_count INTEGER DEFAULT 1;"))
            if gap_columns and "corpus_scope" not in gap_columns:
                conn.execute(text("ALTER TABLE research_gaps ADD COLUMN corpus_scope VARCHAR(255) DEFAULT 'Analyzed Project Corpus';"))

            # 5. gap_evidences migrations
            cursor_ev = conn.execute(text("PRAGMA table_info(gap_evidences);"))
            ev_columns = [row[1] for row in cursor_ev.fetchall()]
            if ev_columns and "section_title" not in ev_columns:
                conn.execute(text("ALTER TABLE gap_evidences ADD COLUMN section_title VARCHAR(255);"))
            if ev_columns and "is_counter_evidence" not in ev_columns:
                conn.execute(text("ALTER TABLE gap_evidences ADD COLUMN is_counter_evidence BOOLEAN DEFAULT 0;"))

            # 6. verification_results migrations
            cursor_vr = conn.execute(text("PRAGMA table_info(verification_results);"))
            vr_columns = [row[1] for row in cursor_vr.fetchall()]
            if vr_columns and "paper_id" not in vr_columns:
                conn.execute(text("ALTER TABLE verification_results ADD COLUMN paper_id VARCHAR(36);"))
            if vr_columns and "claim_text" not in vr_columns:
                conn.execute(text("ALTER TABLE verification_results ADD COLUMN claim_text TEXT;"))
            if vr_columns and "page_number" not in vr_columns:
                conn.execute(text("ALTER TABLE verification_results ADD COLUMN page_number INTEGER;"))
            if vr_columns and "explanation" not in vr_columns:
                conn.execute(text("ALTER TABLE verification_results ADD COLUMN explanation TEXT;"))

            conn.commit()

        logger.info(f"Initialized SQLite database at {DB_PATH} using SQLAlchemy.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e

def check_db_health() -> dict:
    """Verifies SQLite accessibility and returns statistics."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT sqlite_version();"))
            version = result.scalar()
            
            # Count registered projects and papers
            proj_count = conn.execute(text("SELECT COUNT(*) FROM research_projects;")).scalar()
            paper_count = conn.execute(text("SELECT COUNT(*) FROM research_papers;")).scalar()

            return {
                "connected": True,
                "sqlite_version": version,
                "database_path": str(DB_PATH),
                "total_projects": proj_count,
                "total_papers": paper_count
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "connected": False,
            "error": str(e),
            "database_path": str(DB_PATH)
        }
