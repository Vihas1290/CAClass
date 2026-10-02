"""AI & Coding Classroom — Streamlit version.

* Syllabus, Leaderboard, My attendance  -> visible to everyone (read-only)
* Attendance marking + "Taught" ticks   -> teacher only (password login)
* All marks / progress are stored in SQLite, so they survive browser refresh,
  server restarts and new devices.

Run:  streamlit run app.py        (needs streamlit >= 1.40)
"""
import hashlib
import hmac
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

import streamlit as st

st.set_page_config(page_title="AI & Coding Classroom", page_icon="🎓", layout="wide")

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
DB_PATH = os.environ.get("CLASSROOM_DB", "classroom.db")

# SHA-256 of the teacher password. Override with st.secrets / env var:
#   TEACHER_PW_HASH = "<sha256 hex>"
DEFAULT_PW_HASH = "862bbdc3bfc6180b8f78af840624b082120d76b70606f0ff0eb00025bf331617"


def teacher_hash() -> str:
    try:
        
        return st.secrets["TEACHER_PW_HASH"]
    except Exception:
        return os.environ.get("TEACHER_PW_HASH", DEFAULT_PW_HASH)


# --------------------------------------------------------------------------
# DATA
# --------------------------------------------------------------------------
NAMES = [
    "Sriansh Reddy Meda", "Sriya Venna", "Tanya Ali", "Tenzin Khentsey Cha", "Vedant Rajaram B",
    "Ishaan Jangra", "K Nainika Rathod", "Mohammed Ayman", "Nihitha Jarugula", "Riya Skandan Mopuri",
    "Sanika Guptabhaya", "Aanvi Reddy Sama", "Adil Anwar Shaikh", "Aniksh Yadav Bollab", "Ayaansh Bathwal",
    "Bhargavi Bende", "Divisha Modi", "Harshith Reddy Kurri",
]
slug = lambda n: re.sub(r"[^a-z]+", "-", n.lower())
STUDENTS = [{"id": slug(n), "name": n} for n in sorted(NAMES, key=str.casefold)]
NAME_OF = {s["id"]: s["name"] for s in STUDENTS}

# Students not enrolled in the Coding track
CODING_EXCLUDE = {"sanika-guptabhaya", "nihitha-jarugula", "tanya-ali"}


def roster_for(track):
    return [s for s in STUDENTS if track != "Coding" or s["id"] not in CODING_EXCLUDE]


AI = [
    {"t": "AI 101: Understanding Artificial Intelligence",
     "o": "Demystifying Artificial Intelligence: How Computers Learn Patterns.",
     "s": [("What is AI?", "AI uses data to identify patterns and make decisions without thinking or feeling like humans."),
           ("AI vs. Search Engines", "Traditional search retrieves indexed links, whereas Generative AI synthesizes new responses from trained patterns."),
           ("AI in Everyday Life", "Recommender systems, facial recognition, traffic prediction, and automatic sorting."),
           ("Capabilities & Myths", "What AI can do (sort, predict, generate) vs. what it cannot do (feel, reason independently, or guarantee accuracy).")],
     "a": ("“AI or NOT AI?” Challenge", "Sorting everyday tools into AI-powered vs. traditional software categories.")},
    {"t": "Prompt Engineering 101",
     "o": "Prompt Engineering: Driving AI with Clear Human Input.",
     "s": [("What is a Prompt?", "AI output quality directly depends on human input quality."),
           ("The 5-Part Formula", "Role + Task + Context + Constraints + Output structure."),
           ("Framing Persona & Task", "Instructing AI to embody a specific persona (e.g., Grade 6 science teacher) to tailor explanation styles."),
           ("Explanations vs. Answers", "Using prompts that demand step-by-step reasoning and real-world analogies rather than simple copy-paste answers.")],
     "a": ("Prompt Makeover Challenge", "Transforming generic prompts (“Tell me about space”) into rich, constrained instructions.")},
    {"t": "Create with AI",
     "o": "Multimodal Creation: Storytelling, Visuals, and Ideas.",
     "s": [("Text Generation for Creative Writing", "Brainstorming plot twists, poems, and character dialogue."),
           ("Image Generation Fundamentals", "Using descriptive prompts (setting, main character traits, artistic style) to create visuals."),
           ("Human Steering in Creativity", "How human direction guides AI text and visual outputs.")],
     "a": ("AI Story & Illustration Studio", "Writing a mini-story prompt and designing matching cover art.")},
    {"t": "Advanced Prompting",
     "o": "Advanced Prompting: Chaining, Formatting, and Refinement.",
     "s": [("Multi-Turn Refinement", "Asking follow-up questions, correcting errors, and adjusting tone or complexity."),
           ("Structured Outputs", "Prompting for tables, revision lists, quizzes, and flowcharts."),
           ("Prompt Chaining", "Breaking large, complex projects into sequential micro-prompts.")],
     "a": ("Prompt Showdown", "Student teams compete to craft the most precise multi-step prompt for a given task.")},
    {"t": "AI for Study & School",
     "o": "AI as Your Socratic Tutor: Study Smarter, Not Harder.",
     "s": [("The Gold Rule", "AI is a learning assistant to boost understanding, never a homework shortcut."),
           ("Revision Techniques", "Generating practice questions, simplifying complex textbook sections, and creating study schedules."),
           ("Learning from Mistakes", "Using AI to explain wrong answers and test knowledge retention.")],
     "a": ("Textbook Study Pack Challenge", "Converting one textbook chapter into revision notes, 5 quiz questions, and a summary table.")},
    {"t": "AI Detective",
     "o": "AI Detective: Spotting Hallucinations, Fake Info, and Bias.",
     "s": [("What are AI Hallucinations?", "Why AI confidently asserts false information or invents non-existent facts."),
           ("Fact-Checking Workflow", "Verifying claims across multiple reliable sources before trusting output."),
           ("Algorithmic Bias & Deepfakes", "How incomplete or unbalanced training data creates unfair outcomes and misleading imagery.")],
     "a": ("REAL or AI? Investigation", "Inspecting generated text and images to flag errors, hallucinations, and hidden biases.")},
    {"t": "AI Safety & Responsible AI",
     "o": "Digital Citizenship: Safety, Ethics, and Human Control.",
     "s": [("Data Privacy Rules", "What information should NEVER be entered into AI (names, photos, addresses, personal documents)."),
           ("Academic Integrity & Copyright", "Why copying AI content verbatim is unethical and how to properly credit AI assistance."),
           ("Human + AI Collaboration", "Keeping humans in the loop for decision-making and oversight.")],
     "a": ("Ethical Dilemma Debate", "Role-playing stakeholders (students, teachers, parents, tech developers) on real-life AI scenarios.")},
    {"t": "AI Creator Challenge",
     "o": "Capstone Showcase: Solving Real Problems with AI.",
     "s": [("Project Tracks", "Study Buddy, Environmental Sorter, AI Story Studio, Smart School Concept, or AI Tool Invention."),
           ("The 5-Step Project Framework", "1. Identify Problem → 2. AI Solution → 3. Write Prompts → 4. Build/Test → 5. Present."),
           ("Presentation Requirements", "Explaining inputs, outputs, system limitations, and human supervision rules.")],
     "a": ("Capstone Activity", "Final project presentation, peer review, and reflection.")},
]

CODING = [
    {"t": "Python Core Fundamentals", "o": "Indentation, dynamic typing, variable declarations, and control flow (if/elif/else, loops).",
     "k": ["if / elif / else", "for", "while", "type()"]},
    {"t": "Pseudo-Randomness", "o": "Utilizing Python's built-in random library (randint, choice, shuffle) for games and simulations.",
     "k": ["import random", "randint()", "choice()", "shuffle()"]},
    {"t": "Console Project Building", "o": "Structuring interactive CLI applications like number-guessing mini-games.",
     "k": ["input()", "print()", "while True"]},
    {"t": "Streamlit UI & Text Elements", "o": "Introducing Streamlit setup, execution workflows, and text rendering (st.title, st.write, st.markdown).",
     "k": ["streamlit run app.py", "st.title", "st.write", "st.markdown"]},
    {"t": "Interactive Widgets & Layouts", "o": "Designing user interfaces with buttons, sliders, input fields, sidebars, and multi-column containers.",
     "k": ["st.button", "st.slider", "st.text_input", "st.sidebar", "st.columns"]},
    {"t": "Data Presentation & Charts", "o": "Rendering DataFrames (st.dataframe, st.metric) and building dynamic plots (st.line_chart).",
     "k": ["st.dataframe", "st.metric", "st.line_chart"]},
    {"t": "State Management & Optimization", "o": "Preserving user state across app reruns using st.session_state and speeding up computations with @st.cache_data.",
     "k": ["st.session_state", "@st.cache_data"]},
    {"t": "Main Capstone Application", "o": "Integrating Python backend functions with an interactive Streamlit frontend into a deployable application.",
     "k": ["functions", "Streamlit frontend", "deploy"]},
]
TRACKS = {"AI": AI, "Coding": CODING}
LABEL = {"P": "Present", "L": "Late", "A": "Absent"}


def fmt_date(d) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    return f"{d.strftime('%a')}, {d.day} {d.strftime('%b')}"


# --------------------------------------------------------------------------
# DATABASE  (this is the "memory")
# --------------------------------------------------------------------------
SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS sessions(
    id TEXT PRIMARY KEY, date TEXT NOT NULL, track TEXT NOT NULL,
    cls INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS marks(
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('P','L','A')),
    PRIMARY KEY(session_id, student_id));
CREATE TABLE IF NOT EXISTS progress(
    track TEXT NOT NULL, cls INTEGER NOT NULL, taught INTEGER NOT NULL,
    PRIMARY KEY(track, cls));
"""


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


@st.cache_resource
def init_db():
    with db() as con:
        con.executescript(SCHEMA)
    return True


def sid_of(d, track):
    return f"{d.isoformat()}_{track}"


def get_marks(sid):
    with db() as con:
        rows = con.execute("SELECT student_id, status FROM marks WHERE session_id=?", (sid,))
        return {r["student_id"]: r["status"] for r in rows}


def get_session_cls(sid):
    with db() as con:
        r = con.execute("SELECT cls FROM sessions WHERE id=?", (sid,)).fetchone()
        return r["cls"] if r else None


def _prune(con, sid):
    con.execute("DELETE FROM sessions WHERE id=? AND NOT EXISTS "
                "(SELECT 1 FROM marks WHERE session_id=?)", (sid, sid))


def _upsert_session(con, d, track, cls):
    con.execute(
        "INSERT INTO sessions(id,date,track,cls,updated_at) VALUES(?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET cls=excluded.cls, updated_at=excluded.updated_at",
        (sid_of(d, track), d.isoformat(), track, cls, datetime.now().isoformat(timespec="seconds")))


def save_mark(d, track, cls, student_id, status):
    sid = sid_of(d, track)
    with db() as con:
        if status is None:
            con.execute("DELETE FROM marks WHERE session_id=? AND student_id=?", (sid, student_id))
            _prune(con, sid)
        else:
            _upsert_session(con, d, track, cls)
            con.execute(
                "INSERT INTO marks(session_id,student_id,status) VALUES(?,?,?) "
                "ON CONFLICT(session_id,student_id) DO UPDATE SET status=excluded.status",
                (sid, student_id, status))


def mark_all_present(d, track, cls, student_ids):
    with db() as con:
        _upsert_session(con, d, track, cls)
        con.executemany("INSERT OR IGNORE INTO marks(session_id,student_id,status) VALUES(?,?,'P')",
                        [(sid_of(d, track), i) for i in student_ids])


def clear_session(sid):
    with db() as con:
        con.execute("DELETE FROM sessions WHERE id=?", (sid,))


def update_cls(sid, cls):
    with db() as con:
        con.execute("UPDATE sessions SET cls=? WHERE id=?", (cls, sid))


def list_sessions(limit=30):
    with db() as con:
        rows = con.execute(
            "SELECT s.id, s.date, s.track, s.cls, COUNT(m.status) AS tot, "
            "COALESCE(SUM(m.status IN ('P','L')),0) AS att "
            "FROM sessions s LEFT JOIN marks m ON m.session_id=s.id "
            "GROUP BY s.id ORDER BY s.date DESC, s.track LIMIT ?", (limit,))
        return [dict(r) for r in rows]


def student_rates():
    """student_id -> (attended, total) over all sessions."""
    with db() as con:
        rows = con.execute("SELECT student_id, COUNT(*) AS tot, "
                           "SUM(status IN ('P','L')) AS att FROM marks GROUP BY student_id")
        return {r["student_id"]: (r["att"] or 0, r["tot"]) for r in rows}


def track_counts():
    """(student_id, track) -> {'P':n,'L':n,'A':n}"""
    out = {}
    with db() as con:
        rows = con.execute("SELECT m.student_id, s.track, m.status, COUNT(*) AS n FROM marks m "
                           "JOIN sessions s ON s.id=m.session_id GROUP BY 1,2,3")
        for r in rows:
            out.setdefault((r["student_id"], r["track"]), {"P": 0, "L": 0, "A": 0})[r["status"]] = r["n"]
    return out


def student_history(student_id):
    with db() as con:
        rows = con.execute("SELECT s.date, s.track, s.cls, m.status FROM marks m "
                           "JOIN sessions s ON s.id=m.session_id WHERE m.student_id=? "
                           "ORDER BY s.date DESC", (student_id,))
        return [dict(r) for r in rows]


def get_progress():
    with db() as con:
        return {(r["track"], r["cls"]): bool(r["taught"]) for r in con.execute("SELECT * FROM progress")}


def set_progress(track, cls, taught):
    with db() as con:
        con.execute("INSERT INTO progress(track,cls,taught) VALUES(?,?,?) "
                    "ON CONFLICT(track,cls) DO UPDATE SET taught=excluded.taught",
                    (track, cls, int(taught)))


# --------------------------------------------------------------------------
# ACCESS CONTROL (teacher only)
# --------------------------------------------------------------------------
def is_teacher() -> bool:
    return bool(st.session_state.get("teacher"))


def do_login():
    pw = st.session_state.get("pw_input", "")
    ok = hmac.compare_digest(hashlib.sha256(pw.encode()).hexdigest(), teacher_hash())
    st.session_state.pw_input = ""
    if ok:
        st.session_state.teacher = True
        st.session_state.page = "Attendance"
    else:
        st.toast("Incorrect password.", icon="❌")


def do_logout():
    st.session_state.teacher = False
    st.session_state.page = "Syllabus"
    st.toast("Attendance locked", icon="🔒")


# --------------------------------------------------------------------------
# ATTENDANCE (teacher)
# --------------------------------------------------------------------------
def mk(sid, student_id):
    return f"mk_{sid}_{student_id}"


def cur_sid():
    return sid_of(st.session_state.att_date, st.session_state.att_track)


def reload_cls(reset=False):
    stored = get_session_cls(cur_sid())
    st.session_state.att_cls = stored or (1 if reset else st.session_state.att_cls)


def on_cls_change():
    if is_teacher():
        update_cls(cur_sid(), st.session_state.att_cls)


def cb_mark(student_id, key):
    if not is_teacher():
        return
    s = st.session_state
    save_mark(s.att_date, s.att_track, s.att_cls, student_id, s[key])


def _forget_keys():
    sid = cur_sid()
    for stu in STUDENTS:
        st.session_state.pop(mk(sid, stu["id"]), None)


def cb_mark_all():
    if not is_teacher():
        return
    s = st.session_state
    mark_all_present(s.att_date, s.att_track, s.att_cls, [x["id"] for x in roster_for(s.att_track)])
    _forget_keys()
    st.toast("Unmarked students set to Present")


def cb_clear():
    if not is_teacher():
        return
    clear_session(cur_sid())
    _forget_keys()
    st.toast("Marks cleared")


def cb_open_session(d_iso, track, cls):
    st.session_state.update(att_date=date.fromisoformat(d_iso), att_track=track, att_cls=cls)


def go_take(track, n):
    st.session_state.update(att_track=track, att_date=date.today(), att_cls=n, page="Attendance")


def render_attendance():
    if not is_teacher():
        st.warning("Teacher login required.")
        return
    ss = st.session_state
    ss.setdefault("att_date", date.today())
    ss.setdefault("att_track", "AI")
    ss.setdefault("att_cls", 1)

    st.subheader("Attendance")
    st.caption("Mark each student Present (P), Late (L) or Absent (A). Changes are saved automatically.")

    c1, c2, c3 = st.columns(3)
    c1.date_input("Date", key="att_date", on_change=reload_cls)
    c2.selectbox("Track", ["AI", "Coding"], key="att_track", on_change=reload_cls, kwargs={"reset": True})
    track = ss.att_track
    c3.selectbox("Class", list(range(1, len(TRACKS[track]) + 1)), key="att_cls", on_change=on_cls_change,
                 format_func=lambda i: f"Class {i} — {TRACKS[track][i - 1]['t']}")
    lesson = TRACKS[track][ss.att_cls - 1]
    st.info(f"**{track} · {ss.att_cls}** — {lesson['o']}")

    sid = cur_sid()
    marks = get_marks(sid)
    roster = roster_for(track)
    total = len(roster)
    cnt = {k: sum(1 for s in roster if marks.get(s["id"]) == k) for k in "PLA"}
    unmarked = total - sum(cnt.values())
    rate = round((cnt["P"] + cnt["L"]) / total * 100) if total else 0

    m = st.columns(4)
    m[0].metric("Present", cnt["P"])
    m[1].metric("Late", cnt["L"])
    m[2].metric("Absent", cnt["A"])
    m[3].metric("Attendance" + (f" · {unmarked} unmarked" if unmarked else ""), f"{rate}%")

    t1, t2, t3 = st.columns([4, 1.4, 1.2], vertical_alignment="bottom")
    q = t1.text_input("Search students", placeholder="Search students", label_visibility="collapsed").strip().lower()
    t2.button("Mark all present", type="primary", on_click=cb_mark_all)
    with t3.popover("Clear"):
        st.write("Clear every mark for this date & track?")
        st.button("Yes, clear", on_click=cb_clear)

    rates = student_rates()
    with st.container(border=True):
        for i, s in enumerate(roster, 1):
            if q and q not in s["name"].lower():
                continue
            key = mk(sid, s["id"])
            if key not in ss:
                ss[key] = marks.get(s["id"])
            att, tot = rates.get(s["id"], (0, 0))
            a, b, c, d = st.columns([0.5, 4, 1.2, 3], vertical_alignment="center")
            a.markdown(f"`{i:02}`")
            b.markdown(f"**{s['name']}**  \n:gray[{f'Attended {att} of {tot}' if tot else 'No sessions yet'}]")
            c.markdown(f"{round(att / tot * 100)}%" if tot else "—")
            d.segmented_control(s["name"], ["P", "L", "A"], key=key, label_visibility="collapsed",
                                on_change=cb_mark, args=(s["id"], key))
        if q and not any(q in s["name"].lower() for s in roster):
            st.write(f"No student matches “{q}”.")

    with st.sidebar:
        st.subheader("Past sessions")
        hist = list_sessions()
        if not hist:
            st.caption("No sessions saved yet. Marks appear here once you start.")
        for h in hist:
            n = len(roster_for(h["track"]))
            pct = round(h["att"] / n * 100) if n else 0
            st.button(f"{fmt_date(h['date'])} · {h['track']} · Class {h['cls']} · {h['att']}/{n} ({pct}%)",
                      key=f"hist_{h['id']}", on_click=cb_open_session, args=(h["date"], h["track"], h["cls"]))


# --------------------------------------------------------------------------
# SYLLABUS
# --------------------------------------------------------------------------
def cb_taught(track, n, key):
    if is_teacher():
        set_progress(track, n, st.session_state[key])


def render_syllabus():
    st.subheader("Syllabus")
    st.caption("Eight AI classes and eight Python & Streamlit classes."
               + (" Tick a class once it has been taught." if is_teacher() else ""))
    track = st.radio("Track", ["AI", "Coding"], horizontal=True, key="syl_track", label_visibility="collapsed")
    classes = TRACKS[track]
    prog = get_progress()
    done = sum(prog.get((track, i + 1), False) for i in range(len(classes)))
    st.progress(done / len(classes), text=f"{'AI track' if track == 'AI' else 'Python & Streamlit'} — "
                                          f"{done} of {len(classes)} taught")

    for i, c in enumerate(classes, 1):
        taught = prog.get((track, i), False)
        with st.container(border=True):
            n_col, body, act = st.columns([0.8, 6, 2], vertical_alignment="top")
            n_col.markdown(f"#### {i:02}")
            n_col.caption("CLASS" if track == "AI" else "MODULE")
            body.markdown(f"#### {c['t']}" + (" ✅" if taught else ""))
            if track == "Coding":
                body.write(c["o"])
            with act:
                if is_teacher():
                    key = f"taught_{track}_{i}"
                    if key not in st.session_state:
                        st.session_state[key] = taught
                    st.checkbox("Taught", key=key, on_change=cb_taught, args=(track, i, key))
                    st.button("Take attendance →", key=f"take_{track}_{i}", on_click=go_take, args=(track, i))
                else:
                    st.checkbox("Taught", value=taught, disabled=True, key=f"ro_{track}_{i}_{taught}")
            if track == "AI":
                with body.expander(f"{len(c['s']) + 1} slides", expanded=(i == 1)):
                    st.markdown(f"**SLIDE 1 · Title & Overview** — {c['o']}")
                    for j, (h, d) in enumerate(c["s"], 2):
                        st.markdown(f"**SLIDE {j} · {h}** — {d}")
                body.info(f"**Activity · Slide {len(c['s']) + 2}** — **{c['a'][0]}** — {c['a'][1]}")
            else:
                body.markdown(" ".join(f"`{k}`" for k in c["k"]))


# --------------------------------------------------------------------------
# LEADERBOARD
# --------------------------------------------------------------------------
def render_leaderboard():
    st.subheader("Leaderboard")
    st.caption("Ranked by classes attended (Present + Late). Ties are broken by attendance rate.")
    sel = st.radio("Track", ["All", "AI", "Coding"], horizontal=True, key="lb_track", label_visibility="collapsed")
    tracks = ["AI", "Coding"] if sel == "All" else [sel]
    counts = track_counts()

    rows = []
    for s in STUDENTS:
        if not any(s in roster_for(t) for t in tracks):
            continue
        tot_c = {"P": 0, "L": 0, "A": 0}
        for t in tracks:
            for k, v in counts.get((s["id"], t), {}).items():
                tot_c[k] += v
        att, tot = tot_c["P"] + tot_c["L"], sum(tot_c.values())
        rows.append({"name": s["name"], **tot_c, "att": att, "tot": tot})
    if not any(r["tot"] for r in rows):
        st.info("No attendance recorded yet.")
        return
    rows.sort(key=lambda r: (-r["att"], -(r["att"] / r["tot"] if r["tot"] else 0), r["name"]))

    table, rank, prev = [], 0, None
    for i, r in enumerate(rows):
        key = (r["att"], r["tot"])
        if key != prev:
            rank, prev = i + 1, key
        table.append({"Rank": ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else rank,
                      "Student": r["name"], "Present": r["P"], "Late": r["L"], "Absent": r["A"],
                      "Attended": f"{r['att']} / {r['tot']}",
                      "Rate": f"{round(r['att'] / r['tot'] * 100)}%" if r["tot"] else "—"})
    st.dataframe(table, hide_index=True)


# --------------------------------------------------------------------------
# MY ATTENDANCE (read-only)
# --------------------------------------------------------------------------
def cb_me():
    me = st.session_state.get("me")
    if me:
        st.query_params["me"] = me
    else:
        st.query_params.pop("me", None)


def render_mine():
    st.subheader("My attendance")
    st.caption("Read only — choose your name to see your own record.")
    if "me" not in st.session_state and st.query_params.get("me") in NAME_OF:
        st.session_state.me = st.query_params["me"]
    me = st.selectbox("Your name", list(NAME_OF), index=None, key="me", placeholder="Select your name…",
                      format_func=NAME_OF.get, on_change=cb_me)
    if not me:
        st.info("Select your name to see your attendance.")
        return
    rows = student_history(me)
    c = {k: sum(1 for r in rows if r["status"] == k) for k in "PLA"}
    m = st.columns(4)
    m[0].metric("Present", c["P"])
    m[1].metric("Late", c["L"])
    m[2].metric("Absent", c["A"])
    m[3].metric("Attendance", f"{round((c['P'] + c['L']) / len(rows) * 100)}%" if rows else "—")
    if not rows:
        st.info("No attendance recorded for you yet.")
        return
    st.dataframe([{"Date": fmt_date(r["date"]), "Track": r["track"],
                   "Class": f"{r['cls']} — {TRACKS[r['track']][r['cls'] - 1]['t']}",
                   "Status": LABEL[r["status"]]} for r in rows], hide_index=True)


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
init_db()
ss = st.session_state
ss.setdefault("teacher", False)
ss.setdefault("page", "Syllabus")

head, auth = st.columns([5, 1.3], vertical_alignment="center")
with head:
    st.title("🎓 AI & Coding Classroom")
    st.caption(f"{len(STUDENTS)} students ({len(roster_for('Coding'))} in Coding) · 2 tracks · "
               f"{len(AI) + len(CODING)} classes")
with auth:
    if is_teacher():
        st.button("🔓 Lock", on_click=do_logout)
    else:
        with st.popover("🔒 Teacher login"):
            st.text_input("Password", type="password", key="pw_input")
            st.button("Unlock", on_click=do_login)

pages = (["Syllabus", "Attendance", "Leaderboard"] if is_teacher()
         else ["Syllabus", "Leaderboard", "My attendance"])
if ss.page not in pages:
    ss.page = pages[0]
st.radio("Page", pages, key="page", horizontal=True, label_visibility="collapsed")

{"Syllabus": render_syllabus, "Attendance": render_attendance,
 "Leaderboard": render_leaderboard, "My attendance": render_mine}[ss.page]()