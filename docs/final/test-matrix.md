# Final Test Matrix

| Capability | Test / evidence | Status | Relevant commit / document |
| --- | --- | --- | --- |
| Edge replay | Edge Agent replay and single-writer tests；Phase A 曾完成运行时验证 | PASS | `13ba672`; source tests |
| MQTT chain | 私网 MQTT/TLS 路径曾验证；本次交付未重新进行实时链路验收 | LIMITED | historical Phase A evidence |
| Database | 最近完整 PostgreSQL 环境：9 integration tests passed；Phase B/C merge 未启动该环境 | LIMITED | `13ba672`; API integration tests |
| API | Phase B/C gate：33 passed，9 integration tests skipped | PASS | `c940041`; API test suite |
| Model loading | Active XGBoost / shadow TCN metadata and运行时边界曾在 Phase A 验证 | PASS | `13ba672`; API inference tests |
| WebSocket | API realtime coverage及 Dashboard 实时路径 | PASS | `13ba672`; `apps/api/tests/test_realtime.py` |
| Frontend | `npm run build` passed in Phase B/C merge gate | PASS | `c940041` |
| RAG retrieval | Knowledge retrieval relevance/refusal coverage | PASS | `apps/api/tests/test_diagnostics.py` |
| LLM fallback | Missing/unavailable LLM returns constrained template and `LLM analysis unavailable` | PASS | `c940041`; `apps/api/tests/test_diagnostics.py` |
| Citation gate | Returned citations are restricted to retrieved manifest documents; insufficient evidence refuses | PASS | `c940041`; `apps/api/tests/test_diagnostics.py` |
| Rejected binary model | Held-out `WELL-00014` candidate evaluation; model never deployed | NOT APPLICABLE | `docs/phase-b/final-report.md` |

`PASS` 表示有当前或已记录的验证证据；并不代表当前生产实例已经重新验收。`LIMITED` 表示边界或本次未重复执行；`NOT APPLICABLE` 表示该能力不应进入交付运行链路。未执行的 PostgreSQL integration tests 不标为 PASS。
