# Final Test Matrix

| Capability | Test / evidence | Status | Relevant commit / document |
| --- | --- | --- | --- |
| Edge replay | Edge Agent replay and single-writer tests；Phase A runtime verification | PASS | `13ba672`; `docs/phase-a/` |
| MQTT chain | Private MQTT chain and TLS routing verification | LIMITED | `docs/phase-a/wireguard-topology-verification.md` |
| Database | 最近完整 PostgreSQL 环境：9 integration tests passed；Phase B/C merge 未启动该环境 | LIMITED | `docs/phase-a/database-migration-execution.md` |
| API | Phase B/C gate：33 passed，9 integration tests skipped | PASS | `c940041`; API test suite |
| Model loading | Active XGBoost / shadow TCN metadata and runtime boundary verified in Phase A | PASS | `13ba672`; `docs/phase-1-5-acceptance.md` |
| WebSocket | API realtime coverage及 Dashboard 实时路径 | PASS | `13ba672`; `apps/api/tests/test_realtime.py` |
| Frontend | `npm run build` passed in Phase B/C merge gate | PASS | `c940041` |
| RAG retrieval | Knowledge retrieval relevance/refusal coverage | PASS | `apps/api/tests/test_diagnostics.py` |
| LLM fallback | Missing/unavailable LLM returns constrained template and `LLM analysis unavailable` | PASS | `c940041`; `apps/api/tests/test_diagnostics.py` |
| Citation gate | Returned citations are restricted to retrieved manifest documents; insufficient evidence refuses | PASS | `c940041`; `apps/api/tests/test_diagnostics.py` |
| Rejected binary model | Held-out `WELL-00014` candidate evaluation; model never deployed | NOT APPLICABLE | `docs/phase-b/final-report.md` |

`PASS` 表示有当前或已记录的验证证据；`LIMITED` 表示边界或本次未重复执行；`NOT APPLICABLE` 表示该能力不应进入交付运行链路。未执行的 PostgreSQL integration tests 不标为 PASS。
