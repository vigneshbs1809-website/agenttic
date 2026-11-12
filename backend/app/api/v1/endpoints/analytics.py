from fastapi import APIRouter
from backend.app.core.database import get_db

router = APIRouter()

@router.get("/analytics/summary")
async def get_analytics_summary():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. Total papers
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_documents = cursor.fetchone()[0]

        # 2. Total chunks
        cursor.execute("SELECT COUNT(*) FROM document_chunks")
        total_chunks = cursor.fetchone()[0]

        # 3. Average pages
        cursor.execute("SELECT AVG(total_pages) FROM documents WHERE total_pages IS NOT NULL")
        avg_pages = cursor.fetchone()[0] or 0

        # 4. Total queries executed
        cursor.execute("SELECT COUNT(*) FROM query_history")
        total_queries = cursor.fetchone()[0]

        # 5. Documents by year
        cursor.execute("""
        SELECT COALESCE(publication_year, 2024) as yr, COUNT(*) as cnt 
        FROM documents 
        GROUP BY yr 
        ORDER BY yr ASC
        """)
        year_distribution = [{"year": str(r[0]), "papers": r[1]} for r in cursor.fetchall()]

        # 6. Status distribution
        cursor.execute("SELECT processed_status, COUNT(*) FROM documents GROUP BY processed_status")
        status_distribution = [{"status": r[0], "count": r[1]} for r in cursor.fetchall()]

    return {
        "total_documents": total_documents,
        "total_chunks": total_chunks,
        "avg_pages": round(avg_pages, 1),
        "total_queries": total_queries,
        "year_distribution": year_distribution if year_distribution else [{"year": "2024", "papers": 0}],
        "status_distribution": status_distribution
    }

