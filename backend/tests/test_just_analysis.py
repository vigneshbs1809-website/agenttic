import sys
print("STEP 0: Starting python script...", flush=True)

sys.path.insert(0, "D:/Literature-Intelligence-Platform/venv/Lib/site-packages")
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("STEP 1: Importing database...", flush=True)
from backend.app.core.database import SessionLocal
print("STEP 2: Importing entities...", flush=True)
from backend.app.models.entities import PaperAnalysis
print("STEP 3: Importing research_analysis_agent...", flush=True)
from backend.app.services.research_analysis_agent import research_analysis_agent
print("STEP 4: Imports complete!", flush=True)

import asyncio
import traceback

async def run():
    print("STEP 5: Inside run(), opening db session...", flush=True)
    try:
        db = SessionLocal()
        pa = db.query(PaperAnalysis).first()
        print(f"STEP 6: Target paper: {pa.paper_id}", flush=True)
        rep = await research_analysis_agent.analyze_paper(db, pa.paper_id)
        print(f"STEP 7: Analysis dimensions: {len(rep.dimensions)}", flush=True)
        for d in rep.dimensions[:3]:
            print(f"  - {d.dimension_name}: status={d.status}", flush=True)
        db.close()
        print("STEP 8: All done!", flush=True)
    except BaseException as e:
        print("RUN EXCEPTION:", e, flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    print("STEP 4.5: Calling run()...", flush=True)
    try:
        asyncio.run(run())
    except BaseException as e:
        print("MAIN EXCEPTION:", e, flush=True)
        traceback.print_exc()
    print("FINISHED SCRIPT NORMALLY", flush=True)
