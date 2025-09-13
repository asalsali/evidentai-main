from pydantic import BaseModel, Field
from typing import List
from agents import Agent


REPORT_AGENT_INSTRUCTIONS = """
You are a professional police report writer. Using the cleaned transcript and image observations,
produce a structured, concise, objective incident report. Avoid speculation. Use neutral tone.
Include sections: Overview, Timeline Highlights, Persons and Entities, Actions Observed, Conclusion.
"""


class ReportOutput(BaseModel):
    overview: str = Field(description="Short description of incident context and purpose")
    timeline: List[str] = Field(description="Chronological highlights")
    entities: List[str] = Field(description="Key persons, vehicles, items, plates")
    actions: List[str] = Field(description="Notable actions taken or observed")
    conclusion: str = Field(description="Objective close-out statement")


report_summarizer_agent = Agent(
    name="report_summarizer_agent",
    model="gpt-4.1-mini",
    instructions=REPORT_AGENT_INSTRUCTIONS,
    output_type=ReportOutput,
)


