from pydantic import BaseModel, Field
from typing import List, Optional
from agents import Agent


IMAGE_AGENT_INSTRUCTIONS = """
You analyze still images captured from a bodycam video.
Identify key entities relevant for law enforcement: persons, weapons, vehicles, license plates, time/place cues, and noteworthy actions.
Be concise and objective. Avoid speculation beyond what the image shows.
Return a list of per-frame observations.
"""


class EntityObservation(BaseModel):
    entity_type: str = Field(description="Category such as person, weapon, vehicle, plate, other")
    description: str = Field(description="Short factual description of the entity or action")
    confidence: float = Field(description="0-1 confidence estimate", ge=0, le=1)


class FrameObservations(BaseModel):
    frame_index: int = Field(description="Index of frame sampled from video")
    observations: List[EntityObservation] = Field(description="Detected entities/actions in this frame")


class ImageAnalysisOutput(BaseModel):
    frames: List[FrameObservations] = Field(description="Per-frame observations")
    summary: Optional[str] = Field(default=None, description="Brief overall summary of visual content")


image_analysis_agent = Agent(
    name="image_analysis_agent",
    model="gpt-4.1-mini",
    instructions=IMAGE_AGENT_INSTRUCTIONS,
    output_type=ImageAnalysisOutput,
)


