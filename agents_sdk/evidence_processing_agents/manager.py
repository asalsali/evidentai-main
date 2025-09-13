from __future__ import annotations

import os
import asyncio
from dataclasses import dataclass
from typing import List
import base64

from django.conf import settings

from agents import Runner
from openai import OpenAI

from .agents.transcription_agent import transcription_agent, TranscriptionOutput
from .agents.image_analysis_agent import image_analysis_agent, ImageAnalysisOutput
from .agents.report_summarizer_agent import report_summarizer_agent, ReportOutput
from .tools import extract_frames, FrameExtractionArgs
from .utilities import extract_audio_from_video

from main.models import Report


@dataclass
class ProcessingArtifacts:
    audio_path: str
    frame_paths: List[str]


class EvidenceProcessingManager:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.runner = Runner()

    def process_report_sync(self, report_id: int) -> None:
        """Sync wrapper to run the async-ish operations sequentially in a thread."""
        report = Report.objects.get(pk=report_id)
        try:
            report.status = 'extracting'
            report.save(update_fields=["status"])

            artifacts = self._prepare_artifacts(report)

            report.status = 'transcribing'
            report.save(update_fields=["status"])
            transcript_text = self._transcribe_audio(artifacts.audio_path)
            report.transcript_text = transcript_text
            report.save(update_fields=["transcript_text"])

            report.status = 'analyzing_images'
            report.save(update_fields=["status"])
            analysis = self._analyze_frames(artifacts.frame_paths)
            report.image_findings_json = analysis
            report.save(update_fields=["image_findings_json"])

            report.status = 'summarizing'
            report.save(update_fields=["status"])
            summary = self._summarize_report(transcript_text, analysis)
            report.summarized_report = self._format_summary(summary)
            report.status = 'completed'
            report.save(update_fields=["summarized_report", "status"])
        except Exception as exc:  # noqa: BLE001
            report.status = 'failed'
            report.status_message = str(exc)
            report.save(update_fields=["status", "status_message"])

    def _prepare_artifacts(self, report: Report) -> ProcessingArtifacts:
        video_path = report.original_video.path
        audio_path = os.path.join(settings.MEDIA_ROOT, 'audio', f'report_{report.id}.mp3')
        frames_dir = os.path.join(settings.MEDIA_ROOT, 'frames', f'report_{report.id}')
        # Extract audio
        extract_audio_from_video(video_path, audio_path)
        report.extracted_audio.name = os.path.relpath(audio_path, settings.MEDIA_ROOT)
        report.save(update_fields=["extracted_audio"])
        # Sample frames
        frame_paths = extract_frames(FrameExtractionArgs(video_path=video_path, sample_rate_fps=1, output_dir=frames_dir))
        return ProcessingArtifacts(audio_path=audio_path, frame_paths=frame_paths)

    def _transcribe_audio(self, audio_path: str) -> str:
        # Use Whisper via OpenAI
        with open(audio_path, 'rb') as f:
            transcript = self.client.audio.transcriptions.create(
                model='whisper-1',
                file=f,
            )
        raw_text = transcript.text if hasattr(transcript, 'text') else str(transcript)
        cleaned: TranscriptionOutput = asyncio.run(self._run_transcription_agent(raw_text))
        return cleaned.cleaned_transcript

    async def _run_transcription_agent(self, raw_text: str) -> TranscriptionOutput:
        result = await self.runner.run(transcription_agent, raw_text)
        return result.final_output

    def _analyze_frames(self, frame_paths: List[str]):
        # Provide images to the agent as base64 data URLs per SDK guidance for local files
        inputs = []
        for idx, path in enumerate(frame_paths):
            with open(path, 'rb') as img_file:
                b64 = base64.b64encode(img_file.read()).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{b64}"
            inputs.append({
                "role": "user",
                "content": [
                    {"type": "input_text", "text": f"Analyze frame index {idx}."},
                    {"type": "input_image", "image_url": data_url},
                ],
            })
        output: ImageAnalysisOutput = asyncio.run(self._run_image_agent(inputs))
        return output.model_dump()

    async def _run_image_agent(self, inputs):
        result = await self.runner.run(image_analysis_agent, inputs)
        return result.final_output

    def _summarize_report(self, transcript: str, analysis_json: dict):
        prompt = (
            "Cleaned Transcript:\n" + transcript + "\n\n"
            + "Image Analysis Summary:\n" + str(analysis_json)
        )
        return asyncio.run(self._run_report_agent(prompt))

    async def _run_report_agent(self, prompt: str) -> ReportOutput:
        result = await self.runner.run(report_summarizer_agent, prompt)
        return result.final_output

    def _format_summary(self, summary: ReportOutput) -> str:
        lines: List[str] = []
        lines.append("Overview\n" + summary.overview)
        lines.append("\nTimeline Highlights")
        for item in summary.timeline:
            lines.append(f"- {item}")
        lines.append("\nPersons and Entities")
        for e in summary.entities:
            lines.append(f"- {e}")
        lines.append("\nActions Observed")
        for a in summary.actions:
            lines.append(f"- {a}")
        lines.append("\nConclusion\n" + summary.conclusion)
        return "\n".join(lines)


