"""AppController handling persistent session memory, context propagation, and request dispatch to RootOrchestrator."""

import logging
from typing import Dict, Any
from agent.config import settings
from agent.root_orchestrator import RootOrchestrator, export_financial_report, ExportReportRequest
from agent.memory.session_store import PersistentSessionStore
from agent.observability.tracer import trace_span
from agent.observability.logging_config import log_tool_execution

logger = logging.getLogger(__name__)


class AppController:
    """FastAPI-facing controller managing session persistence and dispatching queries to RootOrchestrator."""

    def __init__(self):
        self.reasoning_model = settings.reasoning_model
        self.orchestrator = RootOrchestrator()
        self.session_store = PersistentSessionStore()

    @trace_span("AppController.dispatch")
    def dispatch_query(
        self,
        prompt: str,
        session_id: str = "default_session",
        export_gcs_uri: str = "",
        human_approved_export: bool = False,
    ) -> Dict[str, Any]:
        """Routes user queries directly to ADK RootOrchestrator and manages persistent session memory."""
        if not prompt:
            raise ValueError("No query prompt provided.")

        try:
            # 1. Retrieve persistent session history and construct recent context summary with target company propagation
            raw_history = self.session_store.get_session_history(session_id)
            history_summary = ""
            recent_ticker = ""
            if raw_history:
                turn_lines = []
                for t in raw_history[-4:]:
                    if isinstance(t, dict):
                        u_q = t.get("user_query", "")
                        a_r = t.get("agent_response", "")[:300]
                        turn_lines.append(f"User: {u_q}\nAgent: {a_r}")
                        last_resp = t.get("metadata", {}).get("last_response", {})
                        past_tk = last_resp.get("ticker")
                        if past_tk and past_tk != "SEC":
                            recent_ticker = past_tk

                history_summary = "\n".join(turn_lines)
                if recent_ticker:
                    history_summary += f"\nACTIVE CONVERSATION CONTEXT: The primary target company currently discussed in this thread is '{recent_ticker}'. If the user prompt is a follow-up question without an explicit ticker (e.g. 'company risks', 'operating margin', 'revenue'), assume the target company is '{recent_ticker}'."

            # 2. Run analysis directly using ADK RootOrchestrator
            analysis_res = self.orchestrator.run_analysis(
                user_prompt=prompt,
                context_summary=history_summary,
                session_id=session_id,
            )

            export_status_dict = None
            if export_gcs_uri and analysis_res.get("is_success"):
                export_req = ExportReportRequest(
                    ticker="REPORT",
                    destination_gcs_uri=export_gcs_uri,
                    report_content=analysis_res.get("narrative", ""),
                )
                export_res = export_financial_report(export_req, human_approved=human_approved_export)
                export_status_dict = export_res.model_dump()

            if analysis_res.get("narrative"):
                # 3. Save turn to persistent session store with full response payload metadata
                self.session_store.save_session_turn(
                    session_id=session_id,
                    user_query=prompt,
                    agent_response=analysis_res.get("narrative", ""),
                    metadata={"last_response": analysis_res},
                )
                self.session_store.save_last_response(session_id, analysis_res)

            analysis_res["export_status"] = export_status_dict
            return analysis_res
        except Exception as e:
            err_msg = str(e)
            if "Reauthentication is needed" in err_msg or "RefreshError" in err_msg or "401" in err_msg:
                narrative = "⚠️ GCP Authentication Expired: Reauthentication is needed. Please run `gcloud auth application-default login` in your terminal to re-authenticate with Google Cloud."
            else:
                narrative = f"⚠️ Query execution failed: {err_msg}"

            log_tool_execution("dispatch_query", "outcome", {"error": err_msg}, status="ERROR")
            return {
                "is_success": False,
                "error": err_msg,
                "narrative": narrative,
                "model_used": "failed-auth",
            }
