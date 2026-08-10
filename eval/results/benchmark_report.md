# SEC EDGAR Analyst - Benchmark & Evaluation Report
**Timestamp**: 2026-08-10T16:29:52Z  
**Execution Mode**: `MOCKED`  
**Total Test Cases Evaluated**: 24  

## Executive Metrics Summary
| Metric Category | Score / Metric | Status | Pass Threshold |
| :--- | :---: | :---: | :---: |
| **Math Accuracy %** | `100.0%` | ✅ PASS | 100.0% |
| **Grounding Recall** | `0.3681` | ⚠️ WARN | >= 0.7000 |
| **ROUGE-L F1** | `0.4909` | ⚠️ WARN | >= 0.5000 |
| **LLM Faithfulness** | `1.0000` | ✅ PASS | >= 0.8500 |
| **Answer Relevance** | `1.0000` | ✅ PASS | >= 0.8500 |
| **Execution Error Rate** | `0.0%` | ✅ PASS | 0.0% |
| **Average Latency (ms)** | `2814.82ms` | ✅ PASS | <= 3000ms |

## Case-by-Case Benchmark Results
| Case ID | Ticker | Category | Exec Error | Math Acc % | Grounding Recall | ROUGE-L F1 | LLM Faithfulness | Latency (ms) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `test_001_aapl_revenue` | `AAPL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5882 | 1.0000 | 3286.5ms |
| `test_002_aapl_net_income` | `AAPL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5487 | 1.0000 | 2993.9ms |
| `test_003_msft_revenue` | `MSFT` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 3190.0ms |
| `test_004_msft_operating_income` | `MSFT` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 2188.2ms |
| `test_005_nvda_revenue` | `NVDA` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 2444.6ms |
| `test_006_nvda_operating_income` | `NVDA` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 2434.8ms |
| `test_007_amzn_revenue` | `AMZN` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5664 | 1.0000 | 3215.5ms |
| `test_008_amzn_operating_income` | `AMZN` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.5321 | 1.0000 | 2560.2ms |
| `test_009_meta_revenue` | `META` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.5421 | 1.0000 | 2899.5ms |
| `test_010_googl_revenue` | `GOOGL` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5421 | 1.0000 | 2529.7ms |
| `test_011_tsla_revenue` | `TSLA` | `quantitative_variance` | ✅ OK | 100.0% | 0.5000 | 0.5149 | 1.0000 | 2638.6ms |
| `test_012_tsla_net_income` | `TSLA` | `quantitative_variance` | ✅ OK | 100.0% | 0.0000 | 0.4632 | 1.0000 | 2166.6ms |
| `test_013_meta_risk_factors` | `META` | `qualitative_risk` | ✅ OK | 100.0% | 0.5000 | 0.4872 | 1.0000 | 2354.2ms |
| `test_014_tsla_risk_factors` | `TSLA` | `qualitative_risk` | ✅ OK | 100.0% | 0.5000 | 0.5122 | 1.0000 | 2909.4ms |
| `test_015_aapl_msft_peer_comparison` | `AAPL` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.5234 | 1.0000 | 3201.6ms |
| `test_016_nvda_amzn_peer_comparison` | `NVDA` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.4954 | 1.0000 | 2955.7ms |
| `test_017_edge_zero_prior_period` | `TEST` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.3043 | 1.0000 | 2645.9ms |
| `test_018_edge_invalid_numeric_input` | `TEST` | `edge_case` | ✅ OK | 100.0% | 0.0000 | 0.4368 | 1.0000 | 2373.3ms |
| `test_019_edge_restated_nvda_fiscal_year` | `NVDA` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.5047 | 1.0000 | 3288.6ms |
| `test_020_edge_xbrl_tag_discrepancy` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.5000 | 0.4421 | 1.0000 | 3613.5ms |
| `test_021_edge_ambiguous_period_range` | `AMZN` | `edge_case` | ✅ OK | 100.0% | 0.7333 | 0.3678 | 1.0000 | 2253.1ms |
| `test_022_edge_model_armor_pii_injection` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.0000 | 0.4045 | 1.0000 | 3045.0ms |
| `test_023_edge_2025_filing_availability` | `AAPL` | `edge_case` | ✅ OK | 100.0% | 0.6000 | 0.4615 | 1.0000 | 2781.5ms |
| `test_024_edge_multi_company_citation_isolation` | `NVDA` | `peer_comparison` | ✅ OK | 100.0% | 0.5000 | 0.4848 | 1.0000 | 3585.6ms |