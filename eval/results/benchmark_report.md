# SEC EDGAR Analyst - Benchmark & Evaluation Report
**Timestamp**: 2026-08-13T17:49:27Z  
**Execution Mode**: `MOCKED`  
**Total Test Cases Evaluated**: 39  

## Executive Metrics Summary
| Metric Category | Score / Metric | Status | Pass Threshold |
| :--- | :---: | :---: | :---: |
| **Math Accuracy %** | `100.0%` | ✅ PASS | 100.0% |
| **Grounding Recall** | `0.4509` | ⚠️ WARN | >= 0.7000 |
| **ROUGE-L F1** | `0.6030` | ✅ PASS | >= 0.5000 |
| **LLM Faithfulness** | `1.0000` | ✅ PASS | >= 0.8500 |
| **Answer Relevance** | `1.0000` | ✅ PASS | >= 0.8500 |
| **Execution Error Rate** | `0.0%` | ✅ PASS | 0.0% |
| **Average Latency (ms)** | `3432.23ms` | ⚠️ WARN | <= 3000ms |

## Case-by-Case Benchmark Results
| Case ID | Ticker | Category | Exec Error | Math Acc % | Grounding Recall | ROUGE-L F1 | LLM Faithfulness | Latency (ms) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `test_001_aapl_revenue` | `AAPL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5882 | 1.0000 | 2968.6ms |
| `test_002_aapl_net_income` | `AAPL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5487 | 1.0000 | 2476.4ms |
| `test_003_msft_revenue` | `MSFT` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 3403.9ms |
| `test_004_msft_operating_income` | `MSFT` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 2195.0ms |
| `test_005_nvda_revenue` | `NVDA` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 2409.1ms |
| `test_006_nvda_operating_income` | `NVDA` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 2215.6ms |
| `test_007_amzn_revenue` | `AMZN` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 3183.4ms |
| `test_008_amzn_operating_income` | `AMZN` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.5321 | 1.0000 | 2667.0ms |
| `test_009_meta_revenue` | `META` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.5421 | 1.0000 | 2847.2ms |
| `test_010_googl_revenue` | `GOOGL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5421 | 1.0000 | 2701.9ms |
| `test_011_tsla_revenue` | `TSLA` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5149 | 1.0000 | 2273.3ms |
| `test_012_tsla_net_income` | `TSLA` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 2685.2ms |
| `test_013_meta_risk_factors` | `META` | `qualitative_risk` | ✅ OK | 100.0% | 0.5000 | 0.9048 | 1.0000 | 1345.1ms |
| `test_014_tsla_risk_factors` | `TSLA` | `qualitative_risk` | ✅ OK | 100.0% | 0.5000 | 0.9130 | 1.0000 | 1831.3ms |
| `test_015_aapl_msft_peer_comparison` | `AAPL` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.9333 | 1.0000 | 2815.5ms |
| `test_016_nvda_amzn_peer_comparison` | `NVDA` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.9310 | 1.0000 | 2354.2ms |
| `test_017_edge_zero_prior_period` | `TEST` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.3043 | 1.0000 | 2958.7ms |
| `test_018_edge_invalid_numeric_input` | `TEST` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.9048 | 1.0000 | 2071.1ms |
| `test_019_edge_restated_nvda_fiscal_year` | `NVDA` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.5047 | 1.0000 | 3482.7ms |
| `test_020_edge_xbrl_tag_discrepancy` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.4421 | 1.0000 | 3537.7ms |
| `test_021_edge_ambiguous_period_range` | `AMZN` | `edge_case` | ✅ OK | 100.0% | 0.7333 | 0.3678 | 1.0000 | 2657.7ms |
| `test_022_edge_model_armor_pii_injection` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.9000 | 1.0000 | 2405.3ms |
| `test_023_edge_2025_filing_availability` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.6000 | 0.4615 | 1.0000 | 2574.4ms |
| `test_024_edge_multi_company_citation_isolation` | `NVDA` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.4848 | 1.0000 | 3196.2ms |
| `test_mt_001_aapl_drilldown` | `AAPL` | `multi_turn_drilldown` | ✅ OK | 100.0% | 0.5000 | 0.7282 | 1.0000 | 5253.3ms |
| `test_mt_002_msft_drilldown` | `MSFT` | `multi_turn_drilldown` | ✅ OK | 100.0% | 0.5000 | 0.6840 | 1.0000 | 5058.1ms |
| `test_mt_003_nvda_drilldown` | `NVDA` | `multi_turn_drilldown` | ✅ OK | 100.0% | 0.5000 | 0.6911 | 1.0000 | 4865.8ms |
| `test_mt_004_aapl_anaphora` | `AAPL` | `multi_turn_anaphora` | ✅ OK | 100.0% | 0.5000 | 0.6301 | 1.0000 | 4405.9ms |
| `test_mt_005_msft_anaphora` | `MSFT` | `multi_turn_anaphora` | ✅ OK | 100.0% | 0.5000 | 0.6399 | 1.0000 | 4561.5ms |
| `test_mt_006_nvda_anaphora` | `NVDA` | `multi_turn_anaphora` | ✅ OK | 100.0% | 0.5000 | 0.6515 | 1.0000 | 4302.5ms |
| `test_mt_007_context_switch_aapl_to_msft` | `MSFT` | `multi_turn_context_switch` | ✅ OK | 100.0% | 0.5000 | 0.4292 | 1.0000 | 4580.5ms |
| `test_mt_008_context_switch_msft_to_nvda` | `NVDA` | `multi_turn_context_switch` | ✅ OK | 100.0% | 0.5000 | 0.3632 | 1.0000 | 5395.4ms |
| `test_mt_009_context_switch_nvda_to_aapl` | `AAPL` | `multi_turn_context_switch` | ✅ OK | 100.0% | 0.2500 | 0.8820 | 1.0000 | 3269.1ms |
| `test_mt_010_clarification_aapl` | `AAPL` | `multi_turn_clarification` | ✅ OK | 100.0% | 0.5000 | 0.7667 | 1.0000 | 5104.4ms |
| `test_mt_011_clarification_msft` | `MSFT` | `multi_turn_clarification` | ✅ OK | 100.0% | 0.7500 | 0.7316 | 1.0000 | 4527.6ms |
| `test_mt_012_clarification_nvda` | `NVDA` | `multi_turn_clarification` | ✅ OK | 100.0% | 0.7500 | 0.7421 | 1.0000 | 4178.8ms |
| `test_mt_013_multimetric_aapl` | `AAPL` | `multi_turn_multimetric` | ✅ OK | 100.0% | 0.5000 | 0.4156 | 1.0000 | 5031.6ms |
| `test_mt_014_multimetric_msft` | `MSFT` | `multi_turn_multimetric` | ✅ OK | 100.0% | 0.5000 | 0.3571 | 1.0000 | 4983.0ms |
| `test_mt_015_multimetric_nvda` | `NVDA` | `multi_turn_multimetric` | ✅ OK | 100.0% | 0.5000 | 0.3970 | 1.0000 | 5083.3ms |