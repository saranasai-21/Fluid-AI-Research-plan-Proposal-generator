"""
Fluid AI — Step Executor
Executes each step of the plan sequentially, with retry logic
and context passing between steps.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from agent.llm_client import LLMClient
from models.schemas import ExecutionPlan, PlanStep, StepResult, StepStatus
from config import MAX_RETRIES, RETRY_BASE_DELAY, RETRY_MAX_DELAY

logger = logging.getLogger("fluid_ai.executor")

# ─── Execution Prompt ────────────────────────────────────────────────────────

EXECUTION_SYSTEM_PROMPT = """You are an expert content generation agent working on creating a 
professional business document. You are executing ONE specific step of a larger plan.

Guidelines:
- Generate detailed, professional, realistic content for this step
- Use specific numbers, dates, names, and details (use plausible mock data when needed)
- Write in a professional business tone
- Structure content with clear headings, bullet points, and sections
- Make the content comprehensive — aim for depth, not brevity
- If the step involves creating tables or lists, provide complete, detailed entries
- Use markdown formatting for structure (headers with ##, bullet points, numbered lists, **bold**)

IMPORTANT: Generate ONLY the content for this specific step. Do not repeat previous steps or 
add meta-commentary about the process."""


class Executor:
    """
    Executes plan steps sequentially, passing context from completed steps
    to subsequent ones. Each step has independent retry logic.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def execute_plan(self, plan: ExecutionPlan, user_request: str) -> list[StepResult]:
        """
        Execute all steps in the plan sequentially.

        Args:
            plan: The execution plan to follow.
            user_request: The original user request for context.

        Returns:
            List of StepResult objects with content from each step.
        """
        results: list[StepResult] = []
        logger.info(f"Beginning execution of {len(plan.steps)} steps")

        for step in plan.steps:
            # Build context from previous steps
            context = self._build_context(results)
            result = self._execute_step(step, plan, user_request, context)
            results.append(result)

            if result.status == StepStatus.FAILED:
                logger.warning(
                    f"Step {step.step_number} failed. Continuing with remaining steps..."
                )

        completed = sum(1 for r in results if r.status == StepStatus.COMPLETED)
        logger.info(f"Execution complete: {completed}/{len(results)} steps succeeded")
        return results

    def _execute_step(
        self,
        step: PlanStep,
        plan: ExecutionPlan,
        user_request: str,
        previous_context: str,
    ) -> StepResult:
        """
        Execute a single step with retry logic.

        Returns:
            StepResult with the generated content or error information.
        """
        logger.info(f"Executing step {step.step_number}: {step.title}")

        user_prompt = self._build_step_prompt(step, plan, user_request, previous_context)
        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                content = self.llm.chat(
                    system_prompt=EXECUTION_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    temperature=0.7,
                    max_tokens=4096,
                )

                logger.info(
                    f"Step {step.step_number} completed "
                    f"({len(content)} chars, attempt {attempt})"
                )
                return StepResult(
                    step_number=step.step_number,
                    title=step.title,
                    status=StepStatus.COMPLETED,
                    content=content,
                    retries_used=attempt - 1,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Step {step.step_number} failed (attempt {attempt}/{MAX_RETRIES}): {e}"
                )
                if attempt < MAX_RETRIES:
                    delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), RETRY_MAX_DELAY)
                    time.sleep(delay)

        # All retries exhausted
        logger.error(f"Step {step.step_number} failed after {MAX_RETRIES} attempts")
        return StepResult(
            step_number=step.step_number,
            title=step.title,
            status=StepStatus.FAILED,
            content="",
            retries_used=MAX_RETRIES,
            error_message=f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
        )

    @staticmethod
    def _build_step_prompt(
        step: PlanStep,
        plan: ExecutionPlan,
        user_request: str,
        previous_context: str,
    ) -> str:
        """Build the user prompt for executing a specific step."""
        prompt_parts = [
            f"## Original Request\n{user_request}\n",
            f"## Document Being Created\n"
            f"- Type: {plan.document_type}\n"
            f"- Title: {plan.document_title}\n",
            f"## Current Step ({step.step_number}/{len(plan.steps)})\n"
            f"- Title: {step.title}\n"
            f"- Type: {step.step_type.value}\n"
            f"- Instructions: {step.description}\n",
        ]

        if previous_context:
            prompt_parts.append(
                f"## Content From Previous Steps\n"
                f"Use this context to maintain consistency and build upon:\n\n"
                f"{previous_context}\n"
            )

        prompt_parts.append(
            "## Your Task\n"
            "Generate the content for this step NOW. Be detailed and professional. "
            "Use markdown formatting."
        )

        return "\n".join(prompt_parts)

    @staticmethod
    def _build_context(results: list[StepResult]) -> str:
        """Build context string from previously completed steps."""
        completed = [r for r in results if r.status == StepStatus.COMPLETED and r.content]
        if not completed:
            return ""

        context_parts = []
        for result in completed:
            context_parts.append(f"### {result.title}\n{result.content}")

        return "\n\n---\n\n".join(context_parts)
