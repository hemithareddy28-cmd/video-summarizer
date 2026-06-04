import streamlit as st
import math
import re
import time
from backend import process_video_file, process_youtube_url, generate_pdf, answer_question


def _render_mindmap(mm_data, title):
    cx, cy = 400, 300
    r1, r2 = 130, 225
    items = list(mm_data.items())
    n = max(len(items), 1)
    clrs = ["#6366f1","#8b5cf6","#06b6d4","#10b981","#f59e0b","#ef4444","#ec4899","#84cc16"]
    ns = ls = ""
    for i, (topic, subs) in enumerate(items):
        a = (2*math.pi*i/n) - math.pi/2
        mx, my = cx + r1*math.cos(a), cy + r1*math.sin(a)
        c = clrs[i % len(clrs)]
        ls += f'<line x1="{cx}" y1="{cy}" x2="{mx:.0f}" y2="{my:.0f}" stroke="{c}" stroke-width="1.5" stroke-opacity="0.5" stroke-dasharray="4 3"/>'
        ns += f'<circle cx="{mx:.0f}" cy="{my:.0f}" r="36" fill="{c}" fill-opacity="0.15" stroke="{c}" stroke-width="1.2"/><text x="{mx:.0f}" y="{my:.0f}" text-anchor="middle" dominant-baseline="middle" font-size="10" fill="{c}" font-weight="600" font-family="sans-serif">{topic[:15]}</text>'
        for j, sub in enumerate((subs or [])[:4]):
            na = max(len(subs or []), 1)
            sa = a + 0.55*(j-(na-1)/2)/max(na-1,1)
            sx, sy = cx + r2*math.cos(sa), cy + r2*math.sin(sa)
            ls += f'<line x1="{mx:.0f}" y1="{my:.0f}" x2="{sx:.0f}" y2="{sy:.0f}" stroke="{c}" stroke-width="0.8" stroke-opacity="0.3" stroke-dasharray="2 3"/>'
            ns += f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="24" fill="{c}" fill-opacity="0.07" stroke="{c}" stroke-width="0.7"/><text x="{sx:.0f}" y="{sy:.0f}" text-anchor="middle" dominant-baseline="middle" font-size="8" fill="#94a3b8" font-family="sans-serif">{sub[:14]}</text>'
    st.markdown(f'<svg viewBox="0 0 800 600" xmlns="http://www.w3.org/2000/svg" style="width:100%;background:#0a0f1e;border-radius:12px;border:1px solid rgba(99,102,241,0.2)"><defs><radialGradient id="rg"><stop offset="0%" stop-color="#4f46e5" stop-opacity="0.2"/><stop offset="100%" stop-color="#4f46e5" stop-opacity="0"/></radialGradient></defs><circle cx="{cx}" cy="{cy}" r="180" fill="url(#rg)"/>{ls}<circle cx="{cx}" cy="{cy}" r="52" fill="#4f46e5" fill-opacity="0.2" stroke="#6366f1" stroke-width="1.5"/><text x="{cx}" y="{cy-6}" text-anchor="middle" font-size="11" fill="#a5b4fc" font-weight="700" font-family="sans-serif">{title[:13]}</text><text x="{cx}" y="{cy+10}" text-anchor="middle" font-size="7" fill="#6366f1" font-family="monospace">MIND MAP</text>{ns}</svg>', unsafe_allow_html=True)


def ts_to_sec(t):
    try:
        p = t.split(":")
        return int(p[0])*60 + int(p[1])
    except:
        return 0


def yt_id(url):
    for pat in [r'(?:v=)([a-zA-Z0-9_-]{11})', r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})', r'(?:shorts/)([a-zA-Z0-9_-]{11})']:
        m = re.search(pat, url)
        if m: return m.group(1)
    return ""


st.set_page_config(page_title="VideoMind", page_icon="🎬", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
.stApp{background:#030712!important}
.stApp>div{background:transparent!important}
#MainMenu,footer{visibility:hidden}
.vm-logo{font-family:'Bebas Neue',sans-serif;font-size:3.5rem;line-height:1;background:linear-gradient(135deg,#a5b4fc,#c4b5fd,#67e8f9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.vm-sub{color:#64748b;font-size:.85rem;margin-top:.15rem}
.vm-badge{font-family:'JetBrains Mono',monospace;font-size:.58rem;letter-spacing:.15em;color:#4ade80;background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.3);padding:.2rem .55rem;border-radius:3px;display:inline-block}
.vm-div{height:1px;background:linear-gradient(90deg,transparent,rgba(99,102,241,.25),transparent);margin:.75rem 0}
.chip{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:.63rem;background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.25);color:#a5b4fc;padding:.22rem .6rem;border-radius:4px;margin:.15rem}
.chip-g{background:rgba(74,222,128,.08);border-color:rgba(74,222,128,.25);color:#86efac}
.chip-c{background:rgba(6,182,212,.08);border-color:rgba(6,182,212,.25);color:#67e8f9}
.sg{display:grid;grid-template-columns:repeat(4,1fr);gap:.5rem;margin-bottom:.75rem}
.sb{background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.15);border-radius:10px;padding:.75rem;text-align:center}
.sv{font-family:'Bebas Neue',sans-serif;font-size:1.6rem;line-height:1;background:linear-gradient(135deg,#a5b4fc,#67e8f9);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sl{font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;color:#475569;margin-top:.15rem}
.lbl{font-family:'JetBrains Mono',monospace;font-size:.6rem;letter-spacing:.18em;text-transform:uppercase;color:#6366f1;margin:.5rem 0}
.rb{background:rgba(0,0,0,.25);border:1px solid rgba(99,102,241,.15);border-radius:10px;padding:1rem 1.2rem;font-size:.9rem;line-height:1.75;color:#cbd5e1}
.tl{max-height:300px;overflow-y:auto}
.tr{display:grid;grid-template-columns:60px 1fr;gap:.6rem;padding:.4rem .5rem;border-radius:6px}
.tr:hover{background:rgba(99,102,241,.07)}
.tt{font-family:'JetBrains Mono',monospace;font-size:.66rem;color:#6366f1;background:rgba(99,102,241,.1);padding:.15rem .3rem;border-radius:3px;text-align:center}
.tx{font-size:.84rem;color:#94a3b8;line-height:1.5}
.ig{display:grid;grid-template-columns:1fr 1fr;gap:.6rem}
.ic{background:rgba(0,0,0,.2);border:1px solid rgba(99,102,241,.12);border-radius:8px;padding:.8rem;display:flex;gap:.5rem}
.in{font-family:'Bebas Neue',sans-serif;font-size:1.2rem;color:rgba(99,102,241,.3);min-width:1.3rem}
.it{font-size:.82rem;color:#94a3b8;line-height:1.5}
.cw{display:flex;flex-direction:column;gap:.6rem;max-height:300px;overflow-y:auto;margin-bottom:.75rem}
.cb{padding:.65rem .9rem;border-radius:10px;font-size:.87rem;line-height:1.6;max-width:90%}
.cu{background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.25);color:#c7d2fe;align-self:flex-end}
.ca{background:rgba(15,23,42,.8);border:1px solid rgba(99,102,241,.12);color:#cbd5e1;align-self:flex-start}
.ce{text-align:center;color:#334155;font-size:.85rem;padding:1.5rem}
.tb{background:rgba(0,0,0,.2);border:1px solid rgba(99,102,241,.12);border-radius:10px;padding:1rem;font-size:.85rem;line-height:1.8;color:#64748b;max-height:280px;overflow-y:auto}
.aw{text-align:center;padding:4rem 1rem}
.ai{font-size:3rem;margin-bottom:1rem;display:block}
.at{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;color:#334155;letter-spacing:.08em}
.as{font-size:.82rem;color:#1e293b;margin-top:.4rem}
.pl{font-family:'JetBrains Mono',monospace;font-size:.6rem;letter-spacing:.15em;text-transform:uppercase;color:#6366f1;margin-bottom:.4rem}
</style>
""", unsafe_allow_html=True)

# session state
for k,v in [("results",None),("error",None),("vbytes",None),("vname",None),("yt_stored",""),("src",None),("seek",0),("chat",[]),("apikey",""),("pending_q",None)]:
    if k not in st.session_state: st.session_state[k]=v

# header
h1,h2 = st.columns([3,1])
with h1: st.markdown('<div class="vm-logo">VideoMind</div><div class="vm-sub">Drop a video · get a full AI-powered breakdown</div>', unsafe_allow_html=True)
with h2: st.markdown('<div style="text-align:right;padding-top:.6rem"><div class="vm-badge">● 100% LOCAL · NO API KEY</div></div>', unsafe_allow_html=True)
st.markdown('<div class="vm-div"></div>', unsafe_allow_html=True)

left, right = st.columns([4,6], gap="medium")

with left:
    ty, tf = st.tabs(["🔗 YouTube URL","📁 Local File"])
    with ty:
        st.markdown("")
        yt_url = st.text_input("URL", placeholder="https://youtube.com/watch?v=...", label_visibility="collapsed", key="yt_input")
    with tf:
        st.markdown("")
        uploaded = st.file_uploader("Video", type=["mp4","mov","avi","mkv","webm","m4v"], label_visibility="collapsed")
        if uploaded:
            st.markdown(f'<span class="chip">📄 {uploaded.name}</span> <span class="chip chip-c">{uploaded.size/1048576:.1f} MB</span>', unsafe_allow_html=True)

    st.markdown('<div class="vm-div"></div>', unsafe_allow_html=True)

    with st.expander("⚙ Options"):
        language = st.selectbox("Language", ["Auto-detect","English","Hindi","Spanish","French","German","Japanese","Arabic","Portuguese"])
        summary_length = st.select_slider("Summary depth", options=["Brief","Standard","Detailed"], value="Standard")
        do_ts = st.toggle("Timestamps", value=True)
        do_mm = st.toggle("Mind map",   value=True)

    with st.expander("🤖 Chat API Key (optional)"):
        st.caption("Optional: add Anthropic key for Claude-powered chat. Works without it too.")
        ak = st.text_input("Key", value=st.session_state.apikey, type="password", label_visibility="collapsed", placeholder="sk-ant-...")
        if ak != st.session_state.apikey: st.session_state.apikey = ak

    st.markdown("")
    if st.button("⚡ Summarize Now", use_container_width=True):
        has_yt   = bool(st.session_state.get("yt_input","").strip())
        has_file = uploaded is not None
        if not has_yt and not has_file:
            st.error("Please provide a YouTube URL or upload a video file.")
        else:
            if has_file:
                st.session_state.vbytes = uploaded.getvalue()
                st.session_state.vname  = uploaded.name
                st.session_state.src    = "file"
                st.session_state.yt_stored = ""
            else:
                st.session_state.yt_stored = st.session_state["yt_input"].strip()
                st.session_state.src    = "youtube"
                st.session_state.vbytes = None
            st.session_state.chat = []
            st.session_state.seek = 0
            st.session_state.pending_q = None
            with st.spinner("🎙 Transcribing & analysing…"):
                if has_file:
                    res = process_video_file(uploaded, language=language, summary_length=summary_length, include_timestamps=do_ts, include_mindmap=do_mm)
                else:
                    res = process_youtube_url(st.session_state["yt_input"].strip(), language=language, summary_length=summary_length, include_timestamps=do_ts, include_mindmap=do_mm)
            if "error" in res:
                st.session_state.error   = res["error"]
                st.session_state.results = None
            else:
                st.session_state.results = res
                st.session_state.error   = None

    # player
    if st.session_state.src == "file" and st.session_state.vbytes:
        st.markdown("")
        st.markdown('<div class="pl">▶ Video Preview</div>', unsafe_allow_html=True)
        st.video(st.session_state.vbytes, start_time=int(st.session_state.seek))
    elif st.session_state.src == "youtube" and st.session_state.yt_stored:
        st.markdown("")
        st.markdown('<div class="pl">▶ YouTube Player</div>', unsafe_allow_html=True)
        vid = yt_id(st.session_state.yt_stored)
        if vid:
            seek = int(st.session_state.seek)
            cb = int(time.time())  # cache-buster so browser reloads on seek change
            st.markdown(
                f'<iframe width="100%" height="200" '
                f'src="https://www.youtube.com/embed/{vid}?start={seek}&rel=0&_cb={cb}" '
                f'frameborder="0" allowfullscreen '
                f'style="border-radius:10px;border:1px solid rgba(99,102,241,.2)"></iframe>',
                unsafe_allow_html=True
            )

with right:
    if st.session_state.error:
        st.error(f"⚠ {st.session_state.error}")

    r = st.session_state.results
    if r:
        st.markdown(f'<div class="sg"><div class="sb"><div class="sv">{r.get("duration","—")}</div><div class="sl">Duration</div></div><div class="sb"><div class="sv">{r.get("word_count",0):,}</div><div class="sl">Words</div></div><div class="sb"><div class="sv">{len(r.get("insights",[]))}</div><div class="sl">Insights</div></div><div class="sb"><div class="sv">{len(r.get("timestamps",[]))}</div><div class="sl">Segments</div></div></div>', unsafe_allow_html=True)
        if r.get("title"):
            st.markdown(f'<span class="chip">🎬 {r["title"][:55]}</span> <span class="chip chip-g">✓ Done</span>', unsafe_allow_html=True)
            st.markdown("")

        T1,T2,T3,T4,T5 = st.tabs(["📝 Summary","🕐 Timestamps","💡 Insights","💬 Chat","📜 Transcript"])

        with T1:
            st.markdown('<div class="lbl">AI Summary</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rb">{r.get("summary","—")}</div>', unsafe_allow_html=True)
            st.markdown('<div class="vm-div"></div>', unsafe_allow_html=True)
            st.markdown('<div class="lbl">Concept Mind Map</div>', unsafe_allow_html=True)
            if r.get("mindmap"): _render_mindmap(r["mindmap"], r.get("title","Video"))

        with T2:
            ts = r.get("timestamps",[])
            if ts:
                st.markdown('<div class="lbl">Click any segment to jump to it</div>', unsafe_allow_html=True)
                for i, s in enumerate(ts):
                    c1, c2 = st.columns([1, 4])
                    with c1:
                        if st.button(s["time"], key=f"ts_btn_{i}", use_container_width=True):
                            st.session_state.seek = ts_to_sec(s["time"])
                            st.rerun()
                    with c2:
                        st.markdown(f'<div class="tx" style="padding:.45rem 0">{s["text"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="rb">No timestamp data.</div>', unsafe_allow_html=True)

        with T3:
            st.markdown('<div class="lbl">Key Insights</div>', unsafe_allow_html=True)
            ins = r.get("insights",[])
            if ins:
                st.markdown('<div class="ig">'+"".join(f'<div class="ic"><div class="in">0{i+1}</div><div class="it">{x}</div></div>' for i,x in enumerate(ins))+'</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="rb">No insights extracted.</div>', unsafe_allow_html=True)

        with T4:
            st.markdown('<div class="lbl">Chat with Video</div>', unsafe_allow_html=True)
            transcript = r.get("transcript","")

            # show history
            if st.session_state.chat:
                for m in st.session_state.chat:
                    cls = "cu" if m["role"] == "user" else "ca"
                    st.markdown(f'<div class="cb {cls}">{m["content"]}</div>', unsafe_allow_html=True)
                st.markdown("")
            else:
                st.info("💬 Ask anything about this video below")
                st.markdown("**Quick questions:**")
                c1, c2, c3 = st.columns(3)
                for col, q in zip([c1,c2,c3], ["What is this about?", "Key takeaways?", "How does it start?"]):
                    with col:
                        if st.button(q, key=f"sq_{q[:8]}", use_container_width=True):
                            with st.spinner("Thinking…"):
                                ans = answer_question(transcript, q,
                                    chat_history=st.session_state.chat,
                                    api_key=st.session_state.apikey)
                            st.session_state.chat.append({"role":"user","content":q})
                            st.session_state.chat.append({"role":"assistant","content":ans})
                            st.rerun()

            # form prevents double-submit and works reliably in tabs
            with st.form("chat_form", clear_on_submit=True):
                user_q = st.text_input("Ask a question", placeholder="e.g. What does the speaker say about learning?", label_visibility="collapsed")
                submitted = st.form_submit_button("Send ➤", use_container_width=True)
                if submitted and user_q.strip():
                    with st.spinner("Thinking…"):
                        ans = answer_question(transcript, user_q.strip(),
                            chat_history=st.session_state.chat,
                            api_key=st.session_state.apikey)
                    st.session_state.chat.append({"role":"user","content":user_q.strip()})
                    st.session_state.chat.append({"role":"assistant","content":ans})
                    st.rerun()

            if st.session_state.chat:
                if st.button("🗑 Clear chat", key="clr"):
                    st.session_state.chat = []
                    st.rerun()

        with T5:
            st.markdown('<div class="lbl">Full Transcript</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="tb">{r.get("transcript","—")}</div>', unsafe_allow_html=True)

        st.markdown('<div class="vm-div"></div>', unsafe_allow_html=True)
        txt = "VIDEOMIND RESULTS\n"+"="*50+f"\nTitle: {r.get('title','')}\nDuration: {r.get('duration','')}\n\nSUMMARY\n"+r.get("summary","")+"\n\nKEY INSIGHTS\n"+"\n".join(f"• {i}" for i in r.get("insights",[]))+"\n\nTIMESTAMPS\n"+"\n".join(f'[{s["time"]}] {s["text"]}' for s in r.get("timestamps",[]))+"\n\nTRANSCRIPT\n"+r.get("transcript","")
        d1,d2 = st.columns(2)
        with d1: st.download_button("↓ TXT", data=txt, file_name="videomind.txt", mime="text/plain", use_container_width=True)
        with d2:
            pdf = generate_pdf(r)
            if pdf:
                st.download_button("↓ PDF", data=pdf, file_name="videomind.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.button("↓ PDF (install reportlab)", disabled=True, use_container_width=True)
    else:
        st.markdown('<div class="aw"><span class="ai">🎬</span><div class="at">Awaiting Video</div><div class="as">Paste a YouTube URL or upload a file, then hit Summarize.</div></div>', unsafe_allow_html=True)