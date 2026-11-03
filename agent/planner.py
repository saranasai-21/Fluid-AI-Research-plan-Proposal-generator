"""
Fluid AI — Multi-Step Planner
Uses the LLM to decompose a natural language request into an ordered
execution plan with discrete, actionable steps.
"""

from __future__ import annotations

import logging
from typing import Optional

from agent.llm_client import LLMClient
from models.schemas import ExecutionPlan, PlanStep, StepType

logger = logging.getLogger("fluid_ai.planner")

# ─── Planning Prompt ─────────────────────────────────────────────────────────

PLANNING_SYSTEM_PROMPT = """You are an expert AI planning agent. Your job is to analyze a user's 
natural language request and create a detailed, step-by-step execution plan for producing a 
professional business document.

You must determine:
1. What TYPE of document is needed (project_plan, proposal, sop, meeting_minutes, 
   business_report, technical_design, product_spec, integration_plan, or general)
2. A professional TITLE for the document
3. The specific STEPS needed to create this document

Each step must have:
- step_number: sequential order (1, 2, 3, ...)
- title: short descriptive title  
- description: detailed instructions for what content to generate in this step
- step_type: one of "analyze", "research", "generate", "structure", "review"

Guidelines:
- Always start with an "analyze" step to understand the request
- Use "research" steps to gather information or context about the topic
- Use "generate" steps for creating actual document content (sections, tables, lists)
- Use "structure" steps for organizing content into a coherent document structure
- Always end with a "review" step
- Plan 4-7 steps for most requests
- Be specific about what content each step should produce
- Include relevant details from the user's request in step descriptions

Respond ONLY with a JSON object matching this schema:
{
    "document_type": "string",
    "document_title": "string",
    "steps": [
        {
            "step_number": 1,
            "title": "string",
            "description": "string",
            "step_type": "analyze|research|generate|structure|review"
        }
    ],
    "reasoning": "string explaining your planning rationale"
}"""


class Planner:
    """
    Decomposes natural language requests into structured execution plans
    using LLM-based reasoning.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def create_plan(self, user_request: str) -> ExecutionPlan:
        """
        Generate an execution plan from a user's natural language request.

        Args:
            user_request: The raw user request text.

        Returns:
            A validated ExecutionPlan with ordered steps.

        Raises:
            ValueError: If the LLM response can't be parsed into a valid plan.
            RuntimeError: If the LLM call fails after retries.
        """
        logger.info(f"Creating execution plan for request: {user_request[:100]}...")

        user_prompt = (
            f"Create a detailed execution plan for the following request:\n\n"
            f'"{user_request}"\n\n'
            f"Remember: respond with ONLY the JSON object."
        )

        raw_plan = self.llm.chat_json(
            system_prompt=PLANNING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,  # Lower temperature for more structured output
        )

        # Validate and parse the plan
        plan = self._validate_plan(raw_plan)
        logger.info(
            f"Plan created: '{plan.document_title}' with {len(plan.steps)} steps"
        )
        return plan

    @staticmethod
    def _validate_plan(raw: dict) -> ExecutionPlan:
        """
        Validate and normalize the raw LLM plan output.
        Handles minor formatting inconsistencies from the LLM.
        """
        # Normalize step_type values
        valid_types = {t.value for t in StepType}
        if "steps" in raw:
            for step in raw["steps"]:
                step_type = step.get("step_type", "generate").lower()
                if step_type not in valid_types:
                    # Map common variations
                    type_map = {
                        "analysis": "analyze",
                        "researching": "research",
                        "generating": "generate",
                        "structuring": "structure",
                        "reviewing": "review",
                        "write": "generate",
                        "outline": "structure",
                        "draft": "generate",
                        "compile": "structure",
                        "finalize": "review",
                    }
                    step["step_type"] = type_map.get(step_type, "generate")

        # Ensure steps are numbered correctly
        if "steps" in raw:
            for i, step in enumerate(raw["steps"], 1):
                step["step_number"] = i

        return ExecutionPlan(**raw)
