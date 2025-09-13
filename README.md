# 🚔 Evident AI

**Automatically transforms bodycam footage into professional evidence reports using AI.**

## What It Does

**Input**: Upload a bodycam video file  
**Output**: Complete professional report with transcript, visual analysis, and structured findings

### The Process
1. **Extracts audio** from video and transcribes speech using AI
2. **Analyzes key frames** to identify people, objects, and actions
3. **Generates timeline** of events in chronological order
4. **Creates summary** with entities, actions, and conclusions
5. **Produces report** ready for legal/administrative use

### What You Get
- **Full transcript** of all spoken words
- **Visual analysis** of what happened in the video
- **Timeline** of key events
- **Entity list** of people and objects identified
- **Action summary** of activities observed
- **Professional conclusion** suitable for reports

## Why Use This

- **Saves hours** of manual transcription and analysis
- **Consistent format** for all evidence reports
- **AI accuracy** with human-readable output
- **Immediate results** - no waiting for manual processing
- **Professional quality** reports ready for court/administrative use

## Quick Start

```bash
# Install and run
pip install -r requirements.txt
echo "OPENAI_API_KEY=your_key" > .env
python manage.py migrate
python manage.py runserver
```

Visit `http://localhost:8000`, upload a video, and get your report.

## Requirements

- Python 3.8+
- OpenAI API key
- Video files (MP4, AVI, MOV)

---

*Built for law enforcement, security, and legal professionals who need fast, accurate evidence documentation.*
