from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader

from sentinel_sre.models.actions import ActionExecutionResult, RemediationAction, SafetyVerdict
from sentinel_sre.models.incident import Incident
from sentinel_sre.models.rca import RootCauseAnalysis


class PostMortemReporter:
    """Compiles structured incident reports in Markdown format."""

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir or Path(__file__).parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir), autoescape=False)

    def generate_report(
        self,
        incident: Incident,
        rca: RootCauseAnalysis,
        action: RemediationAction,
        safety_verdict: SafetyVerdict,
        execution_result: ActionExecutionResult,
    ) -> str:
        template = self.jinja_env.get_template("postmortem.md.jinja2")
        return template.render(
            incident=incident,
            rca=rca,
            action=action,
            safety_verdict=safety_verdict,
            execution_result=execution_result,
        )


reporter = PostMortemReporter()
