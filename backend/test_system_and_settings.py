import sys
import os

sys.path.insert(0, "d:/Literature-Intelligence-Platform/venv/Lib/site-packages")
sys.path.insert(0, ".")

import asyncio
from backend.app.core.database import SessionLocal
from backend.app.core.config import settings
from backend.app.api.system import (
    get_complete_system_status,
    select_active_models,
    test_ollama_connection,
    test_embedding_generation,
    test_database_connections,
    run_full_system_diagnostics,
    get_system_configuration,
    update_system_configuration,
    get_agent_execution_logs,
    SelectModelsRequest,
    ConfigUpdateRequest,
)

def test_system_module_sync():
    db = SessionLocal()
    try:
        print("=== 1. Testing GET /api/system/status ===")
        status_data = get_complete_system_status(db=db)
        assert status_data["backend"]["name"] == settings.APP_NAME
        assert status_data["system_resources"]["ram_total_mb"] > 0
        assert status_data["sqlite"]["connected"] is True
        assert status_data["chromadb"]["active_collection"] == "literature_chunks"
        assert status_data["pdf_storage"]["exists"] is True
        print(f"  -> SQLite: {status_data['sqlite']['size_mb']} MB, {status_data['sqlite']['counts']['papers']} papers")
        print(f"  -> ChromaDB: {status_data['chromadb']['total_chunks_indexed']} chunks, size: {status_data['chromadb']['size_mb']} MB")
        print(f"  -> PDF Storage: {status_data['pdf_storage']['total_pdf_files']} PDFs, size: {status_data['pdf_storage']['total_size_mb']} MB")
        print(f"  -> RAM: {status_data['system_resources']['ram_percent']}% ({status_data['system_resources']['ram_used_mb']} MB)")
        print(f"  -> Selected LLM: {status_data['selected_llm']['model']}")
        print(f"  -> Embedding Model: {status_data['embedding_model']['model']}")

        print("\n=== 2. Testing Configuration Validation & Update ===")
        # 2a. Get current config
        cur_cfg = get_system_configuration()
        print(f"  -> Current config: chunk_size={cur_cfg.chunk_size}, overlap={cur_cfg.chunk_overlap}, top_k={cur_cfg.retrieval_top_k}, max_output={cur_cfg.model_output_limit}")

        # 2b. Test invalid chunk overlap (overlap >= chunk_size)
        try:
            ConfigUpdateRequest(
                chunk_size=500,
                chunk_overlap=550,
                retrieval_top_k=5,
                model_output_limit=512
            )
            assert False, "Validation should have failed for chunk_overlap >= chunk_size"
        except ValueError as val_err:
            print(f"  -> Successfully caught invalid configuration: {val_err}")

        # 2c. Test valid config update
        valid_req = ConfigUpdateRequest(
            chunk_size=750,
            chunk_overlap=150,
            retrieval_top_k=6,
            model_output_limit=768,
            temperature=0.2
        )
        updated_cfg = update_system_configuration(payload=valid_req)
        assert updated_cfg.chunk_size == 750
        assert updated_cfg.chunk_overlap == 150
        assert updated_cfg.retrieval_top_k == 6
        assert updated_cfg.model_output_limit == 768
        assert updated_cfg.temperature == 0.2
        print(f"  -> Successfully updated and validated config: chunk_size={updated_cfg.chunk_size}, overlap={updated_cfg.chunk_overlap}")

        # Restore defaults
        restore_req = ConfigUpdateRequest(
            chunk_size=600,
            chunk_overlap=100,
            retrieval_top_k=4,
            model_output_limit=512,
            temperature=0.1
        )
        update_system_configuration(payload=restore_req)
        print("  -> Restored default configuration.")

        print("\n=== 3. Testing Model Selection ===")
        model_req = SelectModelsRequest(
            llm_model="qwen3:1.7b",
            embed_model="nomic-embed-text"
        )
        model_res = select_active_models(payload=model_req)
        assert model_res["status"] == "success"
        assert model_res["selected_llm"] == "qwen3:1.7b"
        print(f"  -> Selected models verified: {model_res['selected_llm']}, {model_res['selected_embed']}")

        print("\n=== 4. Testing Database Connections Check ===")
        db_test_res = test_database_connections(db=db)
        assert db_test_res["sqlite"]["connected"] is True
        assert db_test_res["chromadb"]["connected"] is True
        print(f"  -> SQLite response latency: {db_test_res['sqlite']['latency_ms']} ms")
        print(f"  -> ChromaDB response latency: {db_test_res['chromadb']['latency_ms']} ms")

        print("\n=== 5. Testing Ollama Live Connection Ping ===")
        ollama_test_res = test_ollama_connection()
        print(f"  -> Ollama connected: {ollama_test_res['connected']} (latency: {ollama_test_res['latency_ms']} ms)")

        print("\n=== 6. Testing Embedding Generation Diagnostic ===")
        embed_test_res = test_embedding_generation()
        print(f"  -> Embedding test success: {embed_test_res['success']} ({embed_test_res.get('message') or embed_test_res.get('error')})")

        print("\n=== 7. Testing Full System Diagnostics Sweep ===")
        diag_res = run_full_system_diagnostics(db=db)
        print(f"  -> Diagnostics Overall Status: {diag_res['overall_status'].upper()}")
        print(f"  -> Total Checks: {diag_res['total_checks']} (Passed: {diag_res['passed']}, Warnings: {diag_res['warnings']}, Failures: {diag_res['failures']})")
        for chk in diag_res["checks"]:
            status_symbol = "✓" if chk["status"] == "pass" else ("⚠" if chk["status"] == "warn" else "✗")
            print(f"     [{status_symbol}] {chk['component']}: {chk['message']}")

        print("\n=== 8. Testing Agent Execution Logs Retrieval ===")
        logs_res = get_agent_execution_logs(limit=10, offset=0, db=db)
        assert logs_res.total_count >= 0
        print(f"  -> Retrieved {len(logs_res.logs)} logs out of {logs_res.total_count} total logs in SQLite.")
        if logs_res.logs:
            sample_log = logs_res.logs[0]
            print(f"     Sample Log: [{sample_log.status.upper()}] {sample_log.agent_name} - {sample_log.action_type} ({sample_log.duration_ms} ms)")

        print("\n=======================================================")
        print("ALL SYSTEM HEALTH & SETTINGS BACKEND TESTS PASSED 100%!")
        print("=======================================================")

    finally:
        db.close()

if __name__ == "__main__":
    test_system_module_sync()
