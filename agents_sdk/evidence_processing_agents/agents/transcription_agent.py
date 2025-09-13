from pydantic import BaseModel, Field
from agents import Agent


TRANSCRIPTION_AGENT_INSTRUCTIONS = """
You are a transcription post-processor. You receive raw text transcripts from Whisper.
Your task is to clean obvious errors, add simple punctuation, and produce a clean transcript.
Return only the cleaned transcript text.
"""


class TranscriptionOutput(BaseModel):
    cleaned_transcript: str = Field(description="Cleaned transcript with basic punctuation and corrections")


transcription_agent = Agent(
    name="transcription_agent",
    model="gpt-4.1-mini",
    instructions=TRANSCRIPTION_AGENT_INSTRUCTIONS,
    output_type=TranscriptionOutput,
)


