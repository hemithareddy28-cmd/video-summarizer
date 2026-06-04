"""
VideoMind — backend.py
Enhanced with: timestamps, mind map generation, faster transcription,
word-frequency chart data, and PDF export.
"""

from __future__ import annotations
import os, re, subprocess, tempfile, math, collections
from typing import Optional
from io import BytesIO

# ── Optional heavy imports (graceful fallback) ────────────────────────────────
try:
    from faster_whisper import WhisperModel
    _WHISPER_OK = True
except ImportError:
    _WHISPER_OK = False

try:
    from sumy.parsers.plaintext import PlaintextParser
    from sumy.nlp.tokenizers    import Tokenizer
    from sumy.summarizers.lsa   import LsaSummarizer
    from sumy.nlp.stemmers      import Stemmer
    from sumy.utils             import get_stop_words
    _SUMY_OK = True
except ImportError:
    _SUMY_OK = False

try:
    from reportlab.lib.pagesizes  import A4
    from reportlab.lib            import colors as rl_colors
    from reportlab.lib.styles     import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units      import cm
    from reportlab.platypus       import (SimpleDocTemplate, Paragraph, Spacer,
                                          Table, TableStyle, HRFlowable)
    _PDF_OK = True
except ImportError:
    _PDF_OK = False

# ── Config ────────────────────────────────────────────────────────────────────
_LENGTH_SENTENCES = {"Brief": 4, "Standard": 8, "Detailed": 14}
_WHISPER_MODEL: Optional["WhisperModel"] = None

_STOP_WORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","i","you","he",
    "she","it","we","they","this","that","these","those","not","no","so","as",
    "if","by","from","up","about","into","through","during","before","after",
    "above","below","between","out","off","over","under","then","than","also",
    "just","more","some","all","any","each","both","its","our","their","your",
    "my","his","her","what","which","who","whom","how","when","where","why",
    "very","too","such","even","like","well","back","still","here","there",
}

# ── Whisper model loader ──────────────────────────────────────────────────────
def _get_whisper() -> "WhisperModel":
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = WhisperModel("tiny", compute_type="int8")
    return _WHISPER_MODEL


# ── Audio extraction ──────────────────────────────────────────────────────────
def _extract_audio_ffmpeg(input_path: str, output_path: str) -> float:
    """Extract mono 16 kHz MP3 from video. Returns duration in seconds."""
    subprocess.run(
        ["ffmpeg", "-i", input_path, "-vn", "-ar", "16000",
         "-ac", "1", "-ab", "64k", "-f", "mp3", output_path, "-y"],
        capture_output=True, check=True
    )
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True
    )
    try:
        return float(res.stdout.strip())
    except Exception:
        return 0.0


# ── Transcription with timestamps ────────────────────────────────────────────
def _transcribe(audio_path: str, language: str, include_timestamps: bool = True):
    """
    Returns (full_transcript: str, timestamps: list[dict]).
    timestamps = [{"time": "0:00", "text": "..."}, ...]
    """
    lang_param = None if language == "Auto-detect" else language.lower()[:2]
    model = _get_whisper()
    segments, _ = model.transcribe(
        audio_path,
        language=lang_param,
        beam_size=1,
        best_of=1,
        temperature=0,
        vad_filter=False,
    )

    full_parts  = []
    ts_list     = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        full_parts.append(text)
        if include_timestamps:
            start = seg.start
            mins  = int(start // 60)
            secs  = int(start % 60)
            ts_list.append({"time": f"{mins}:{secs:02d}", "text": text})

    return " ".join(full_parts).strip(), ts_list


# ── Summarization ─────────────────────────────────────────────────────────────
def _summarize(transcript: str, summary_length: str) -> dict:
    sentences = [s.strip() for s in re.split(r'[.!?]+', transcript) if len(s.strip()) > 15]

    # Fallback for very short transcripts
    if len(sentences) < 3:
        return {
            "summary": transcript.strip() or "No speech detected in this video.",
            "insights": sentences[:5] if sentences else ["No insights available."],
        }

    sentence_count = _LENGTH_SENTENCES.get(summary_length, 8)

    if _SUMY_OK:
        try:
            parser    = PlaintextParser.from_string(transcript, Tokenizer("english"))
            stemmer   = Stemmer("english")
            summarizer = LsaSummarizer(stemmer)
            summarizer.stop_words = get_stop_words("english")

            summary_sents  = summarizer(parser.document, sentence_count)
            summary        = " ".join(str(s) for s in summary_sents)

            insight_sents  = summarizer(parser.document, 12)
            summary_set    = set(str(s) for s in summary_sents)
            insights, seen = [], set()
            for s in insight_sents:
                t = str(s).strip()
                if t not in seen and t not in summary_set and len(t) > 20:
                    insights.append(t)
                    seen.add(t)
                if len(insights) >= 8:
                    break
            # Pad with summary sentences if too few
            if len(insights) < 5:
                for s in summary_sents:
                    t = str(s).strip()
                    if t not in seen:
                        insights.append(t)
                        seen.add(t)
                    if len(insights) >= 5:
                        break

            return {"summary": summary or transcript[:400], "insights": insights[:8]}
        except Exception:
            pass

    # Plain fallback — pick every Nth sentence
    step    = max(1, len(sentences) // sentence_count)
    summary = " ".join(sentences[i] for i in range(0, len(sentences), step))[:800]
    insights = sentences[:8]
    return {"summary": summary, "insights": insights}


# ── Mind map generator ────────────────────────────────────────────────────────
def _extract_topic_label(sentence: str) -> str:
    """Pull a short 1-3 word label from a sentence — the first meaningful noun phrase."""
    # Remove filler starts
    sentence = re.sub(r'^(so|and|but|also|now|then|well|i|we|you|they|this|that)\s+', '', sentence.strip(), flags=re.I)
    # Grab first 3 meaningful words
    words = [w for w in sentence.split() if len(w) > 2][:5]
    # Try to find a capitalized noun or strong content word
    for w in words:
        clean = re.sub(r'[^a-zA-Z]', '', w)
        if clean and clean[0].isupper() and clean.lower() not in _STOP_WORDS:
            return clean
    # Fallback: first content word
    for w in words:
        clean = re.sub(r'[^a-zA-Z]', '', w).lower()
        if clean and clean not in _STOP_WORDS and len(clean) > 3:
            return clean.title()
    return words[0].title() if words else "Topic"


def _build_mindmap(transcript: str, insights: list[str]) -> dict:
    """
    Build a meaningful mind map using insights as main topics.
    Each topic gets subtopics extracted from the sentences most related to it.
    """
    if not transcript or not insights:
        return {}

    sentences = [s.strip() for s in re.split(r'[.!?]+', transcript) if len(s.strip()) > 20]
    if not sentences:
        return {}

    # Build word frequency for the whole transcript
    all_words = re.findall(r'\b[a-zA-Z]{4,}\b', transcript)
    freq = collections.Counter(w.lower() for w in all_words if w.lower() not in _STOP_WORDS)

    mindmap = {}
    used_labels = set()

    for insight in insights[:6]:
        # Get a clean short label for this topic
        label = _extract_topic_label(insight)
        # Avoid duplicate labels
        if label in used_labels:
            words_in_insight = [w for w in insight.split() if w.lower() not in _STOP_WORDS and len(w) > 3]
            label = words_in_insight[1].title() if len(words_in_insight) > 1 else label + "+"
        used_labels.add(label)

        # Find the top content words in this specific insight sentence
        insight_words = re.findall(r'\b[a-zA-Z]{4,}\b', insight)
        insight_keys  = [w.lower() for w in insight_words if w.lower() not in _STOP_WORDS]

        # Find related sentences in transcript that share keywords with this insight
        related_words = collections.Counter()
        for sent in sentences:
            sent_lower = sent.lower()
            if any(kw in sent_lower for kw in insight_keys[:3]):
                sent_words = re.findall(r'\b[a-zA-Z]{4,}\b', sent)
                for w in sent_words:
                    wl = w.lower()
                    if wl not in _STOP_WORDS and wl not in insight_keys:
                        related_words[wl] += freq.get(wl, 1)

        # Pick top 4 related words as subtopics
        subtopics = [w.title() for w, _ in related_words.most_common(4)]
        mindmap[label] = subtopics

    return mindmap


# ── Utility ───────────────────────────────────────────────────────────────────
def _format_duration(secs: float) -> str:
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


# ── Main entry points ─────────────────────────────────────────────────────────
def process_video_file(uploaded_file, api_key: str = "", language: str = "Auto-detect",
                       summary_length: str = "Standard", model=None,
                       include_timestamps: bool = True,
                       include_mindmap: bool = True) -> dict:
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, uploaded_file.name)
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        audio_path = os.path.join(tmpdir, "audio.mp3")

        try:
            duration_sec = _extract_audio_ffmpeg(video_path, audio_path)
        except Exception as e:
            return {"error": f"Audio extraction failed: {e}. Ensure ffmpeg is on PATH."}

        try:
            transcript, ts_list = _transcribe(audio_path, language, include_timestamps)
        except Exception as e:
            return {"error": f"Transcription failed: {e}"}

        try:
            ai = _summarize(transcript, summary_length)
        except Exception as e:
            return {"error": f"Summarization failed: {e}"}

        mm = _build_mindmap(transcript, ai["insights"]) if include_mindmap else {}

        return {
            "title":      os.path.splitext(uploaded_file.name)[0],
            "duration":   _format_duration(duration_sec),
            "source":     uploaded_file.name,
            "transcript": transcript,
            "summary":    ai["summary"],
            "insights":   ai["insights"],
            "timestamps": ts_list,
            "mindmap":    mm,
            "word_count": len(transcript.split()),
        }


def process_youtube_url(url: str, api_key: str = "", language: str = "Auto-detect",
                        summary_length: str = "Standard", model=None,
                        include_timestamps: bool = True,
                        include_mindmap: bool = True) -> dict:
    try:
        import yt_dlp  # type: ignore
    except ImportError:
        return {"error": "yt-dlp not installed. Run: pip install yt-dlp"}

    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, "audio.mp3")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmpdir, "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "64",
            }],
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info       = ydl.extract_info(url, download=True)
                title      = info.get("title", "YouTube Video")
                duration_s = float(info.get("duration", 0))
                # find downloaded mp3
                for fname in os.listdir(tmpdir):
                    if fname.endswith(".mp3"):
                        audio_path = os.path.join(tmpdir, fname)
                        break
        except Exception as e:
            return {"error": f"Download failed: {e}"}

        try:
            transcript, ts_list = _transcribe(audio_path, language, include_timestamps)
        except Exception as e:
            return {"error": f"Transcription failed: {e}"}

        try:
            ai = _summarize(transcript, summary_length)
        except Exception as e:
            return {"error": f"Summarization failed: {e}"}

        mm = _build_mindmap(transcript, ai["insights"]) if include_mindmap else {}

        return {
            "title":      title,
            "duration":   _format_duration(duration_s),
            "source":     url,
            "transcript": transcript,
            "summary":    ai["summary"],
            "insights":   ai["insights"],
            "timestamps": ts_list,
            "mindmap":    mm,
            "word_count": len(transcript.split()),
        }


# ── PDF generation ────────────────────────────────────────────────────────────
def generate_pdf(r: dict) -> bytes:
    if not _PDF_OK:
        return b""
    try:
        return _build_pdf(r)
    except Exception as e:
        print(f"PDF error: {e}")
        return b""


def _build_pdf(r: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    AW = 16.6 * cm

    title_st = ParagraphStyle("VM_Title",
        fontName="Helvetica-Bold", fontSize=24, leading=28,
        textColor=rl_colors.HexColor("#1e1b4b"), spaceAfter=2)
    sub_st = ParagraphStyle("VM_Sub",
        fontName="Helvetica", fontSize=10, leading=14,
        textColor=rl_colors.HexColor("#374151"), spaceAfter=8)
    h2_st = ParagraphStyle("VM_H2",
        fontName="Helvetica-Bold", fontSize=12, leading=16,
        textColor=rl_colors.HexColor("#4338ca"),
        spaceBefore=16, spaceAfter=6)
    body_st = ParagraphStyle("VM_Body",
        fontName="Helvetica", fontSize=10, leading=16,
        textColor=rl_colors.HexColor("#111827"), spaceAfter=6)
    bullet_st = ParagraphStyle("VM_Bullet",
        fontName="Helvetica", fontSize=10, leading=15,
        textColor=rl_colors.HexColor("#1f2937"),
        leftIndent=16, spaceAfter=5, bulletIndent=4)
    mono_st = ParagraphStyle("VM_Mono",
        fontName="Courier", fontSize=8.5, leading=13,
        textColor=rl_colors.HexColor("#1f2937"), spaceAfter=3)
    ts_body_st = ParagraphStyle("VM_TS",
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=rl_colors.HexColor("#111827"))
    ts_time_st = ParagraphStyle("VM_TSTime",
        fontName="Courier-Bold", fontSize=9, leading=13,
        textColor=rl_colors.HexColor("#4338ca"))

    def hr():
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=0.6,
                                color=rl_colors.HexColor("#c7d2fe"),
                                spaceAfter=6, spaceBefore=2))

    story = []

    # ── Header ──
    story.append(Paragraph("VideoMind", title_st))
    title_text = r.get('title', '')[:100]
    story.append(Paragraph(title_text, sub_st))

    # ── Meta table ──
    meta_data = [[
        f"Duration: {r.get('duration','—')}",
        f"Words: {r.get('word_count',0):,}",
        f"Insights: {len(r.get('insights',[]))}",
        f"Segments: {len(r.get('timestamps',[]))}",
    ]]
    col_w = AW / 4
    meta_t = Table(meta_data, colWidths=[col_w]*4)
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), rl_colors.HexColor("#eef2ff")),
        ("FONTNAME",      (0,0),(-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8.5),
        ("TEXTCOLOR",     (0,0),(-1,-1), rl_colors.HexColor("#4338ca")),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOX",           (0,0),(-1,-1), 1,   rl_colors.HexColor("#a5b4fc")),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, rl_colors.HexColor("#c7d2fe")),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
    ]))
    story.append(meta_t)
    hr()

    # ── Summary ──
    story.append(Paragraph("AI Summary", h2_st))
    story.append(Paragraph(r.get("summary", "—"), body_st))
    hr()

    # ── Key Insights ──
    story.append(Paragraph("Key Insights", h2_st))
    for i, ins in enumerate(r.get("insights", []), 1):
        story.append(Paragraph(f"<b>{i:02d}.</b>  {ins}", bullet_st))
    hr()

    # ── Timestamps ──
    ts_list = r.get("timestamps", [])
    if ts_list:
        story.append(Paragraph("Timestamped Segments", h2_st))

        ts_style = ts_body_st
        ts_time_style = ts_time_st

        # Build rows with Paragraph objects so text wraps properly
        ts_rows = [[
            Paragraph("<b>Time</b>", ts_time_style),
            Paragraph("<b>Segment</b>", ts_style)
        ]]
        for seg in ts_list:
            ts_rows.append([
                Paragraph(seg["time"], ts_time_style),
                Paragraph(seg["text"], ts_style)
            ])

        TIME_COL = 1.8 * cm
        TEXT_COL = AW - TIME_COL
        ts_t = Table(ts_rows, colWidths=[TIME_COL, TEXT_COL], repeatRows=1)
        ts_t.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",    (0,0),(-1,0),  rl_colors.HexColor("#4338ca")),
            ("TEXTCOLOR",     (0,0),(-1,0),  rl_colors.white),
            ("FONTNAME",      (0,0),(-1,0),  "Helvetica-Bold"),
            # Data rows alternating
            ("ROWBACKGROUNDS",(0,1),(-1,-1),
             [rl_colors.white, rl_colors.HexColor("#f5f3ff")]),
            ("FONTSIZE",      (0,0),(-1,-1), 9),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("BOX",           (0,0),(-1,-1), 0.5, rl_colors.HexColor("#c7d2fe")),
            ("INNERGRID",     (0,0),(-1,-1), 0.3, rl_colors.HexColor("#e0e7ff")),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("RIGHTPADDING",  (0,0),(-1,-1), 6),
        ]))
        story.append(ts_t)
        hr()

    # ── Transcript ──
    story.append(Paragraph("Full Transcript", h2_st))
    transcript = r.get("transcript", "—")
    # Split into sentences for clean paragraphs
    paras = [s.strip() for s in re.split(r'(?<=[.!?])\s+', transcript) if s.strip()]
    # Group into ~3 sentences per paragraph
    groups = [" ".join(paras[i:i+3]) for i in range(0, len(paras), 3)]
    for grp in groups[:60]:
        story.append(Paragraph(grp, mono_st))

    doc.build(story)
    return buf.getvalue()


# ── Chat / Q&A ────────────────────────────────────────────────────────────────
def _smart_local_qa(transcript: str, question: str, chat_history: list[dict]) -> str:
    """
    Smart local Q&A — no API needed. Handles:
    - Summary/overview questions
    - Who/what/when/where/why/how questions
    - Topic-specific questions
    - Follow-up questions using chat history
    """
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', transcript) if len(s.strip()) > 20]
    if not sentences:
        return "No transcript available to answer from."

    q = question.lower().strip()

    # ── Detect question type ──
    is_summary   = any(w in q for w in ["summary","summarize","overview","about","topic","main","overall","cover"])
    is_who       = q.startswith("who")
    is_what      = q.startswith("what")
    is_when      = q.startswith("when")
    is_how_many  = "how many" in q or "how much" in q
    is_list      = any(w in q for w in ["list","examples","mention","points","ways","steps","types"])
    is_first     = any(w in q for w in ["first","begin","start","introduction","intro","opening"])
    is_last      = any(w in q for w in ["last","end","conclusion","finally","closing"])
    is_explain   = any(w in q for w in ["explain","describe","elaborate","detail","mean","means"])

    # ── Build context from prior chat if follow-up ──
    follow_up_words = {"it","this","that","they","them","their","he","she","more","also","else","other"}
    is_follow_up = bool(chat_history) and any(w in q.split() for w in follow_up_words)
    context_words = set()
    if is_follow_up and chat_history:
        last_q = chat_history[-2]["content"] if len(chat_history) >= 2 else ""
        context_words = set(re.findall(r'\b[a-z]{4,}\b', last_q.lower())) - _STOP_WORDS

    # ── Summary type ──
    if is_summary:
        n = min(5, max(3, len(sentences) // 10))
        step = max(1, len(sentences) // n)
        picked = [sentences[i] for i in range(0, len(sentences), step)][:n]
        return "This video covers: " + " ".join(picked)

    # ── First/last part ──
    if is_first:
        return "The video begins with: " + " ".join(sentences[:3])
    if is_last:
        return "The video concludes with: " + " ".join(sentences[-3:])

    # ── Score sentences by relevance ──
    q_words = (set(re.findall(r'\b[a-z]{3,}\b', q)) - _STOP_WORDS) | context_words

    scored = []
    for i, sent in enumerate(sentences):
        s_words = set(re.findall(r'\b[a-z]{3,}\b', sent.lower()))
        overlap = len(q_words & s_words)

        # TF bonus — prefer sentences with rare/specific matching words
        tf_bonus = sum(1 for w in (q_words & s_words)
                       if sum(1 for s in sentences if w in s.lower()) < len(sentences) * 0.3)

        # Proximity bonus — boost sentences near other good ones
        prox_bonus = 0
        if scored and abs(i - scored[-1][2]) <= 2:
            prox_bonus = 1

        score = overlap + tf_bonus * 0.5 + prox_bonus * 0.3
        scored.append((score, tf_bonus, i, sent))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top_scored = [(score, i, sent) for score, _, i, sent in scored if score > 0]

    if not top_scored:
        return "I couldn't find relevant information about that in the transcript. Try rephrasing or ask something else."

    # ── Format response based on question type ──
    if is_list:
        items = [sent for _, _, sent in top_scored[:5]]
        numbered = "\n".join(f"{n+1}. {s}" for n, s in enumerate(items))
        return f"Here are the relevant points mentioned:\n{numbered}"

    if is_how_many or is_when or is_who:
        # Return single most relevant sentence + context
        best = top_scored[0][2]
        context_sents = []
        for _, idx, sent in top_scored[:3]:
            context_sents.append(sent)
        return " ".join(context_sents)

    # Default: return top 3 relevant sentences as a coherent answer
    # Sort by position in transcript for natural reading order
    top3 = sorted(top_scored[:3], key=lambda x: x[1])
    answer = " ".join(sent for _, _, sent in top3)

    # Add a natural prefix based on question type
    if is_what:
        return "Based on the video: " + answer
    if is_explain:
        return "The video explains: " + answer
    return answer


def answer_question(transcript: str, question: str,
                    chat_history: list[dict] | None = None,
                    api_key: str = "") -> str:
    """
    Answer a question about the video transcript.
    Uses Claude API if api_key is provided, else uses smart local QA.
    """
    if not transcript:
        return "No transcript available. Please process a video first."

    history = chat_history or []

    if not api_key:
        return _smart_local_qa(transcript, question, history)

    # ── Claude API path ──
    import urllib.request, json as _json

    messages = []
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})

    system_prompt = (
        "You are VideoMind Assistant. You have been given the full transcript of a video. "
        "Answer the user's questions based ONLY on the transcript content. "
        "Be concise, direct, and cite relevant parts of the transcript. "
        "If the answer isn't in the transcript, say so clearly.\n\n"
        f"TRANSCRIPT:\n{transcript[:12000]}"
    )

    payload = _json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 600,
        "system": system_prompt,
        "messages": messages,
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read())
            return data["content"][0]["text"]
    except Exception:
        return _smart_local_qa(transcript, question, history)
