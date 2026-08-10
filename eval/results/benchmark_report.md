# SEC EDGAR Analyst - Benchmark & Evaluation Report
**Timestamp**: 2026-08-10T18:54:08Z  
**Execution Mode**: `MOCKED`  
**Total Test Cases Evaluated**: 22  

## Executive Metrics Summary
| Metric Category | Score / Metric | Status | Pass Threshold |
| :--- | :---: | :---: | :---: |
| **Math Accuracy %** | `100.0%` | ✅ PASS | 100.0% |
| **Grounding Recall** | `0.3515` | ⚠️ WARN | >= 0.7000 |
| **ROUGE-L F1** | `0.4925` | ⚠️ WARN | >= 0.5000 |
| **LLM Faithfulness** | `1.0000` | ✅ PASS | >= 0.8500 |
| **Answer Relevance** | `1.0000` | ✅ PASS | >= 0.8500 |
| **Execution Error Rate** | `0.0%` | ✅ PASS | 0.0% |
| **Average Latency (ms)** | `1306.92ms` | ✅ PASS | <= 3000ms |

## Case-by-Case Benchmark Results
| Case ID | Ticker | Category | Exec Error | Math Acc % | Grounding Recall | ROUGE-L F1 | LLM Faithfulness | Latency (ms) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `test_001_aapl_revenue` | `AAPL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5882 | 1.0000 | 2272.7ms |
| `test_002_aapl_net_income` | `AAPL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5487 | 1.0000 | 1450.4ms |
| `test_003_msft_revenue` | `MSFT` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 1212.9ms |
| `test_004_msft_operating_income` | `MSFT` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 1355.1ms |
| `test_005_nvda_revenue` | `NVDA` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 1231.8ms |
| `test_006_nvda_operating_income` | `NVDA` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 1405.8ms |
| `test_007_amzn_revenue` | `AMZN` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 1335.1ms |
| `test_008_amzn_operating_income` | `AMZN` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.5321 | 1.0000 | 1718.1ms |
| `test_009_meta_revenue` | `META` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.5421 | 1.0000 | 1464.7ms |
| `test_010_googl_revenue` | `GOOGL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5421 | 1.0000 | 1352.8ms |
| `test_011_tsla_revenue` | `TSLA` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5149 | 1.0000 | 1424.9ms |
| `test_012_tsla_net_income` | `TSLA` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 1208.0ms |
| `test_013_meta_risk_factors` | `META` | `qualitative_risk` | ✅ OK | 100.0% | 0.5000 | 0.4872 | 1.0000 | 1294.5ms |
| `test_014_tsla_risk_factors` | `TSLA` | `qualitative_risk` | ✅ OK | 100.0% | 0.5000 | 0.5122 | 1.0000 | 1188.5ms |
| `test_015_aapl_msft_peer_comparison` | `AAPL` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.5234 | 1.0000 | 1478.3ms |
| `test_016_nvda_amzn_peer_comparison` | `NVDA` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.4954 | 1.0000 | 1309.4ms |
| `test_017_edge_zero_prior_period` | `TEST` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.3043 | 1.0000 | 493.5ms |
| `test_018_edge_invalid_numeric_input` | `TEST` | `edge_case` | ✅ OK | 100.0% | 0.0000 | 0.4368 | 1.0000 | 460.8ms |
| `test_019_edge_restated_nvda_fiscal_year` | `NVDA` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.5047 | 1.0000 | 1317.3ms |
| `test_020_edge_xbrl_tag_discrepancy` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.4421 | 1.0000 | 1330.2ms |
| `test_021_edge_ambiguous_period_range` | `AMZN` | `edge_case` | ✅ OK | 100.0% | 0.7333 | 0.3678 | 1.0000 | 1221.8ms |
| `test_022_edge_model_armor_pii_injection` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.0000 | 0.4045 | 1.0000 | 1225.5ms |