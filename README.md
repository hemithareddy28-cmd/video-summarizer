# AI Video Summarizer

An AI-powered video summarization application that transforms lengthy videos into concise, structured insights. The application automatically generates transcripts, extracts key topics, creates summaries, identifies important timestamps, and enables interactive chat-based exploration of video content.

Built as a mini project using Python, Streamlit, and modern Natural Language Processing (NLP) techniques.

---
## 🌐 Live Demo

🔗 https://video-summarizer-gkgvfjjyqt8ycdwtswdr7t.streamlit.app/

## Overview

AI Video Summarizer helps users quickly understand video content without watching the entire video. By combining speech-to-text transcription, keyword extraction, summarization, and conversational querying, the system provides an efficient way to analyze educational, informational, and long-form video content.

The application supports multilingual videos and allows users to export generated summaries in both PDF and TXT formats.

---

## Features

### Video Transcription
- Automatic speech-to-text conversion
- Accurate transcription using Faster Whisper
- Support for multilingual content

### AI-Powered Summarization
- Generates concise summaries from video transcripts
- Reduces lengthy content into key insights
- Improves information accessibility

### Keyword Extraction
- Identifies important topics and concepts
- Highlights frequently discussed themes
- Enables faster content understanding

### Timestamp Generation
- Captures important moments within videos
- Helps users navigate directly to relevant sections
- Enhances content exploration

### Interactive Chat Interface
- Ask questions about the video content
- Receive context-aware responses based on transcripts
- Improves user engagement and information retrieval

### Export Functionality
- Download summaries as PDF documents
- Export summaries as TXT files
- Easy sharing and documentation

### Multilingual Support
- Handles videos in multiple languages
- Broadens accessibility for diverse users

---

## Technologies Used

- Python
- Streamlit
- Faster Whisper
- Sumy
- NLTK
- yt-dlp
- ReportLab

---

## Project Architecture

```text
Video Input
      │
      ▼
Audio Extraction
      │
      ▼
Speech-to-Text (Whisper)
      │
      ▼
Transcript Generation
      │
 ┌────┼────┐
 ▼    ▼    ▼
Summary Keywords Timestamps
      │
      ▼
Interactive Chat
      │
      ▼
PDF / TXT Export
```

## Applications

- Educational Video Analysis
- Lecture Summarization
- Research Content Review
- Online Learning Platforms
- Podcast and Webinar Insights
- Knowledge Extraction from Long Videos

---

## Learning Outcomes

This project helped me gain practical experience in:

- Natural Language Processing (NLP)
- Speech Recognition Systems
- Streamlit Application Development
- Transcript Processing
- Information Extraction
- AI-Assisted Content Analysis
- Python-Based Software Development

---

## Future Enhancements

- Advanced LLM-based summarization
- Sentiment analysis
- Multi-video comparison
- Cloud deployment
- User authentication
- Real-time video processing

---
## Note

The application fully supports local video uploads for transcription and summarization.

YouTube URL processing may be restricted in some cloud-hosted environments due to platform-specific access limitations.
