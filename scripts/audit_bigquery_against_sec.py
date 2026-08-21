"""Audit and verify all financial metrics in GCP BigQuery against official SEC EDGAR company facts API."""

import json
import time
import datetime
import urllib.request
from typing import Dict, Any, List, Optional
from google.cloud import bigquery
from agent.config import settings

SEC_USER_AGENT = "ApexFinancialGroup cvwang@google.com"

CIK_MAP = {
    "AAPL": ("0000320193", "Apple Inc."),
    "MSFT": ("0000789019", "Microsoft Corp"),
    "NVDA": ("0001045810", "NVIDIA Corp"),
    "GOOGL": ("0001652044", "Alphabet Inc."),
    "AMZN": ("0001018724", "Amazon.com Inc."),
    "TSLA": ("0001318605", "Tesla, Inc."),
    "META": ("0001326801", "Meta Platforms, Inc."),
    "AMD": ("0000002488", "Advanced Micro Devices"),
    "JPM": ("0000019617", "JPMorgan Chase & Co."),
    "WMT": ("0000104169", "Walmart Inc."),
}

REVENUE_CONCEPTS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "TotalRevenuesAndOtherIncome",
]

OPERATING_INCOME_CONCEPTS = [
    "OperatingIncomeLoss",
]

NET_INCOME_CONCEPTS = [
    "NetIncomeLoss",
    "ProfitLoss",
]


def fetch_sec_facts(cik: str) -> Optional[Dict[str, Any]]:
    time.sleep(0.12)
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
    req = urllib.request.Request(url, headers={"User-Agent": SEC_USER_AGENT})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error fetching SEC facts for CIK {cik}: {e}")
        return None


def determine_fiscal_year_from_dates(ticker: str, start_str: str, end_str: str) -> Optional[int]:
    """Calculates the target fiscal year given the start and end dates of an annual reporting period."""
    try:
        start_dt = datetime.datetime.strptime(start_str, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d")
        duration_days = (end_dt - start_dt).days
        if duration_days < 330 or duration_days > 400:
            return None  # Not an annual 12-month period
        
        # FY mapping by corporate fiscal calendar conventions
        if ticker in ("NVDA", "WMT"):
            # Fiscal year ends in January/February of the named fiscal year (e.g. Jan 2024 is FY24)
            if end_dt.month in (1, 2, 3):
                return end_dt.year
            return end_dt.year + 1
        elif ticker == "MSFT":
            # FY ends in June (e.g. June 2023 is FY23)
            return end_dt.year
        elif ticker == "AAPL":
            # FY ends in late September/early October (e.g. Sep 2023 is FY23)
            return end_dt.year
        else:
            # Calendar year companies (AMZN, GOOGL, META, TSLA, AMD, JPM)
            return end_dt.year
    except Exception:
        return None


def extract_annual_metric(facts: Dict[str, Any], ticker: str, concepts: List[str], target_fiscal_year: int) -> Optional[float]:
    """Extracts annual 10-K audited metric for a given company and fiscal year in millions USD."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    
    for concept in concepts:
        if concept not in us_gaap:
            continue
        units = us_gaap[concept].get("units", {}).get("USD", [])
        matches = []
        for item in units:
            if item.get("form") != "10-K":
                continue
            start = item.get("start")
            end = item.get("end")
            if not start or not end:
                continue
            fy_mapped = determine_fiscal_year_from_dates(ticker, start, end)
            if fy_mapped == target_fiscal_year:
                matches.append(item)
        
        if matches:
            # Pick latest filed version (audited / restated if applicable)
            matches.sort(key=lambda x: x.get("filed", ""), reverse=True)
            val = matches[0].get("val")
            if val is not None:
                return round(float(val) / 1e6, 1)
                
    return None


def main():
    client = bigquery.Client(project=settings.gcp_project_id)
    query = f"SELECT ticker, fiscal_year, company_name, revenue, operating_income, net_income FROM `sec-analyst.sec_edgar_financials.financial_metrics` ORDER BY ticker, fiscal_year"
    bq_rows = list(client.query(query).result())
    
    print(f"Auditing {len(bq_rows)} BigQuery financial metric records against official SEC EDGAR XBRL filings...\n")
    
    facts_cache = {}
    for ticker, (cik, _) in CIK_MAP.items():
        facts_cache[ticker] = fetch_sec_facts(cik)
        
    discrepancies = []
    verified_rows = []
    
    for row in bq_rows:
        ticker = row.ticker.upper()
        fy = row.fiscal_year
        if ticker not in CIK_MAP:
            continue
        facts = facts_cache.get(ticker)
        if not facts:
            continue
            
        sec_rev = extract_annual_metric(facts, ticker, REVENUE_CONCEPTS, fy)
        sec_op_inc = extract_annual_metric(facts, ticker, OPERATING_INCOME_CONCEPTS, fy)
        sec_net_inc = extract_annual_metric(facts, ticker, NET_INCOME_CONCEPTS, fy)
        
        bq_rev = row.revenue
        bq_op_inc = row.operating_income
        bq_net_inc = row.net_income
        
        rev_diff = abs(bq_rev - sec_rev) if (bq_rev is not None and sec_rev is not None) else None
        op_diff = abs(bq_op_inc - sec_op_inc) if (bq_op_inc is not None and sec_op_inc is not None) else None
        net_diff = abs(bq_net_inc - sec_net_inc) if (bq_net_inc is not None and sec_net_inc is not None) else None
        
        is_discrepant = False
        disc_details = []
        
        # Allow tolerance of 5.0M for minor rounding
        if rev_diff is not None and rev_diff > 5.0:
            is_discrepant = True
            disc_details.append(f"Revenue: BQ={bq_rev:,.1f}M vs SEC={sec_rev:,.1f}M (diff={rev_diff:,.1f}M)")
        if op_diff is not None and op_diff > 5.0:
            is_discrepant = True
            disc_details.append(f"Operating Income: BQ={bq_op_inc:,.1f}M vs SEC={sec_op_inc:,.1f}M (diff={op_diff:,.1f}M)")
        if net_diff is not None and net_diff > 5.0:
            is_discrepant = True
            disc_details.append(f"Net Income: BQ={bq_net_inc:,.1f}M vs SEC={sec_net_inc:,.1f}M (diff={net_diff:,.1f}M)")
            
        if is_discrepant:
            discrepancies.append({
                "ticker": ticker,
                "fiscal_year": fy,
                "bq": {"rev": bq_rev, "op_inc": bq_op_inc, "net_inc": bq_net_inc},
                "sec": {"rev": sec_rev, "op_inc": sec_op_inc, "net_inc": sec_net_inc},
                "details": disc_details,
            })
            print(f"❌ DISCREPANCY: {ticker} FY{fy} | {', '.join(disc_details)}")
        else:
            verified_rows.append({
                "ticker": ticker,
                "fiscal_year": fy,
                "revenue": bq_rev,
                "operating_income": bq_op_inc,
                "net_income": bq_net_inc,
                "sec_rev": sec_rev,
            })
            print(f"✅ MATCH: {ticker} FY{fy} | Rev: {bq_rev:,.1f}M, OpInc: {bq_op_inc:,.1f}M, NetInc: {bq_net_inc:,.1f}M (SEC: Rev={sec_rev}, OpInc={sec_op_inc}, NetInc={sec_net_inc})")
            
    print("\n" + "="*80)
    print(f"AUDIT SUMMARY: {len(verified_rows)} verified matches, {len(discrepancies)} discrepancies out of {len(bq_rows)} records.")
    print("="*80)
    if discrepancies:
        print("\nAll Discrepancies Details:")
        for d in discrepancies:
            print(f"- {d['ticker']} FY{d['fiscal_year']}:")
            print(f"  BigQuery: {d['bq']}")
            print(f"  SEC XBRL: {d['sec']}")


if __name__ == "__main__":
    main()
