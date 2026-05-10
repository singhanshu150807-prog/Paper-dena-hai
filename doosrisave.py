import sqlite3
import random
import os # Hosting ke liye zaroori
from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "mission_ground_2026_hardcore") # Security update
DB_PATH = "/tmp/exam.db"

# --- DATABASE SETUP ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY, q TEXT, a TEXT, b TEXT, c TEXT, d TEXT, ans INTEGER)")
        
        c.execute("SELECT COUNT(*) FROM questions")
        if c.fetchone()[0] == 0:
            jee_data = [
                ("A ball of mass 10 kg moving with $10\\sqrt{3}$ m/s hits a 20 kg ball at rest. After collision, 1st ball stops. 2nd ball breaks into two equal pieces: one goes along Y-axis at 10 m/s, other at 20 m/s at angle $\\theta$ with X-axis. $\\theta$ is:", "30°", "45°", "60°", "90°", 0),
                ("A 0.1 kg bullet hits a 1.9 kg block at 20 m/s and sticks. Table height is 1m. Kinetic energy just before the system strikes the floor is: (g=10)", "19 J", "23 J", "20 J", "21 J", 3),
                ("Two particles of mass m with velocities $u\\hat{i}$ and $u(\\hat{i}+\\hat{j})/2$ collide inelastically. Energy lost is:", "3/4 mu²", "2/√3 mu²", "1/3 mu²", "1/8 mu²", 3),
                ("Mass m projected at u, $\\theta=\\pi/3$. At max height, it collides inelastically with same mass moving at $u\\hat{j}$. Horizontal distance covered by combined mass is:", "3√3/8 (u²/g)", "2√2 (u²/g)", "5/8 (u²/g)", "3√2/4 (u²/g)", 0),
                ("Mass m dropped from h, another mass m thrown up at $\\sqrt{2gh}$. They collide head-on inelastically. Time taken for combined mass to reach ground (in units of $\\sqrt{h/g}$) is:", "√(1/2)", "√(3/4)", "√(3/2)", "√(4/3)", 2)
            ]
            c.executemany("INSERT INTO questions (q, a, b, c, d, ans) VALUES (?, ?, ?, ?, ?, ?)", jee_data)
        conn.commit()

# --- FANCY CSS & JS ---
COMMON_STYLE = '''
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&display=swap');
    :root { 
        --primary: #4f46e5; --bg: #0b0f1a; --card-bg: #161e2d;
        --ans: #10b981; --wrong: #ef4444; --rev: #a855f7; --not-ans: #f43f5e;
        --fancy-glow: 0 0 15px rgba(79, 70, 229, 0.4);
    }
    body { font-family: 'Space Grotesk', sans-serif; background: var(--bg); color: #f8fafc; margin: 0; perspective: 1000px; overflow-x: hidden; }
    
    @keyframes move {
        0% { transform: translateY(0px) translateX(0px); }
        50% { transform: translateY(-20px) translateX(10px); }
        100% { transform: translateY(0px) translateX(0px); }
    }
    body::after {
        content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image: radial-gradient(#1e293b 1px, transparent 1px);
        background-size: 30px 30px; opacity: 0.3; z-index: -1; animation: move 10s infinite linear;
    }

    .glass-card { 
        background: rgba(22, 30, 45, 0.95); backdrop-filter: blur(20px); padding: 40px; border-radius: 25px; 
        border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 15px 35px rgba(0,0,0,0.4); transition: 0.3s; 
    }
    .glass-card:hover { transform: translateY(-5px); border-color: rgba(79, 70, 229, 0.5); box-shadow: var(--fancy-glow); }
    
    .q-view { display: none; background: var(--card-bg); padding: 30px; border-radius: 20px; animation: slideIn 0.4s ease-out; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .q-view.active { display: block; }
    @keyframes slideIn { from { opacity: 0; transform: translateZ(-100px) translateY(20px); } to { opacity: 1; transform: translateZ(0) translateY(0); } }
    
    .palette-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
    .p-btn { 
        width: 40px; height: 40px; border-radius: 12px; border: none; background: #334155; color: white; 
        cursor: pointer; font-weight: bold; transition: 0.3s; display: flex; align-items: center; justify-content: center; 
        position: relative; box-shadow: 0 4px 6px rgba(0,0,0,0.2); 
    }
    .p-btn.answered { background: var(--ans) !important; }
    .p-btn.not-answered { background: var(--not-ans) !important; }
    .p-btn.review { background: var(--rev) !important; }
    .p-btn.answered-review { background: var(--rev) !important; border: 3px solid var(--ans) !important; }
    .p-btn.active { transform: scale(1.2) translateY(-5px); border: 2px solid white; box-shadow: var(--fancy-glow); z-index: 10; }
    
    .option-row { display: block; padding: 18px; margin: 12px 0; background: #1e293b; border-radius: 15px; cursor: pointer; border: 2px solid transparent; transition: 0.2s; transform-style: preserve-3d; }
    .option-row:hover { background: #2d3a4f; border-color: var(--primary); transform: translateZ(15px) translateX(8px); box-shadow: 5px 5px 15px rgba(0,0,0,0.3); }
    
    .fancy-input {
        width:100%; padding:14px; margin:10px 0; background:#0f172a; border:1px solid #334155; 
        color:white; border-radius:12px; transition: 0.3s;
    }
    .fancy-input:focus { border-color: var(--primary); box-shadow: var(--fancy-glow); outline: none; }
    
    .btn-primary { 
        width:100%; background:var(--primary); color:white; padding:16px; border:none; 
        border-radius:14px; font-weight:bold; cursor:pointer; margin-top:15px; 
        transition: 0.3s; box-shadow: 0 5px 15px rgba(79,70,229,0.3);
    }
    .btn-primary:hover { transform: translateY(-3px); box-shadow: var(--fancy-glow); }
</style>
<script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
'''

@app.route('/')
def home(): return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u, p, c = request.form['username'], request.form['password'], request.form['creator_name'].lower().strip()
        if c != "saksham":
            flash("Creator ka naam galat hai! System hang ho jayega.")
            return redirect('/login')
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            user = conn.execute("SELECT * FROM users WHERE username=?", (u,)).fetchone()
        if user and check_password_hash(user['password'], p):
            session['user'] = u
            return redirect('/exam')
        flash("Password galat hai bhai, dhyan se!")
    return render_template_string(AUTH_HTML, title="System Login 🔐", link="/register", link_text="naya hai kya bhai to yahan daba", gif_url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3o0cTM1Y2k5bmZ6YXBtNm8wdmE2ZGp1YjhkZGRyZ2YxampiaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/3o7TKSjRrfIPjeiZfG/giphy.gif")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p, c = request.form['username'], request.form['password'], request.form['creator_name'].lower().strip()
        if c != "saksham":
            flash("Saksham bhai ka naam likho respect ke saath!")
            return redirect('/register')
        hp = generate_password_hash(p)
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (u, hp))
            return redirect('/login')
        except: flash("Ye ID pehle se booked hai!")
    return render_template_string(AUTH_HTML, title="Naya Khata Kholo ✨", link="/login", link_text="Login Karo", gif_url="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3o0cTM1Y2k5bmZ6YXBtNm8wdmE2ZGp1YjhkZGRyZ2YxampiaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/LmNtrBBlqvL5YshW30/giphy.gif")

@app.route('/exam')
def exam():
    if 'user' not in session: return redirect('/login')
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        qs = [dict(row) for row in conn.execute("SELECT * FROM questions").fetchall()]
    random.shuffle(qs)
    return render_template_string(EXAM_HTML, questions=qs, user=session['user'])

@app.route('/submit', methods=['POST'])
def submit():
    if 'user' not in session: return redirect('/login')
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        qs = conn.execute("SELECT id, ans FROM questions").fetchall()
    
    correct, wrong, skipped = 0, 0, 0
    for q in qs:
        user_val = request.form.get(str(q['id']))
        if user_val is None: skipped += 1
        elif int(user_val) == q['ans']: correct += 1
        else: wrong += 1

    total_score = (correct * 4) - (wrong * 1)
    max_score = len(qs) * 4
    perc = (total_score / max_score) * 100 if max_score > 0 else 0

    if perc >= 85:
        msg, clr, gif = "Oye hoye! Maa ka laadla... kacche faad diye tune toh! 🔥🥳", "var(--ans)", "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3o0cTM1Y2k5bmZ6YXBtNm8wdmE2ZGp1YjhkZGRyZ2YxampiaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/jIs75f1Zos4p1d02I4/giphy.gif"
    elif perc >= 50:
        msg, clr, gif = "Bich mein latka reh gaya... Gali ka kutta na ghar ka na ghat ka! 🐕😕", "#60a5fa", "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3o0cTM1Y2k5bmZ6YXBtNm8wdmE2ZGp1YjhkZGRyZ2YxampiaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/26ufcVAp3AiJJsrIs/giphy.gif"
    elif perc >= 20:
        msg, clr, gif = "Abe ye kya bavasir tatti number hain? Sharam kar le thodi! 💩🤮", "#fbbf24", "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3o0cTM1Y2k5bmZ6YXBtNm8wdmE2ZGp1YjhkZGRyZ2YxampiaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/A5coF7K42Q7f2/giphy.gif"
    else:
        msg, clr, gif = "Bhai chhod de padhaai, gaon chala ja aur kheti seekh le! 🚜😭", "var(--wrong)", "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3o0cTM1Y2k5bmZ6YXBtNm8wdmE2ZGp1YjhkZGRyZ2YxampiaSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/10tIjpzM494fHG/giphy.gif"

    return render_template_string(RESULT_HTML, score=total_score, max=max_score, c=correct, w=wrong, s=skipped, msg=msg, color=clr, result_gif=gif)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# --- TEMPLATES ---

AUTH_HTML = COMMON_STYLE + '''
<div style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding: 20px;">
    <div class="glass-card" style="width:100%; max-width:420px; text-align:center;">
        <img src="{{gif_url}}" alt="Study GIF" style="width:100px; border-radius:50%; margin-bottom:15px; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <h2 style="color:var(--primary); margin:0;">JEE Mock 2026</h2>
        <p style="color:#94a3b8; margin-bottom:20px;">{{ title }} bhai, system phadna h!</p>
        {% with messages = get_flashed_messages() %}{% if messages %}{% for m in messages %}
        <div style="color:var(--wrong); margin-bottom:10px; font-weight:bold;">⚠️ {{ m }}</div>
        {% endfor %}{% endif %}{% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username 👤" required class="fancy-input">
            <input type="password" name="password" placeholder="Password 🔑" required class="fancy-input">
            <input type="text" name="creator_name" placeholder="Owner? (Saksham) 👑" required class="fancy-input">
            <button type="submit" class="btn-primary">chll paper Dene 🚀</button>
        </form>
        <p style="margin-top:25px; text-align:center;"><a href="{{ link }}" style="color:var(--primary); text-decoration:none; font-weight:500;">{{ link_text }}</a></p>
    </div>
</div>
'''

EXAM_HTML = COMMON_STYLE + '''
<div style="background:#1e293b; padding:18px; display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid var(--primary); position:sticky; top:0; z-index:100; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
    <h4 style="margin:0; color:var(--primary); font-size:1.3rem;">IIT-JEE 2026 | {{user}} 🧑‍💻</h4>
    <div id="timer" style="color:var(--wrong); font-weight:bold; font-size:1.3rem; background: rgba(239, 68, 68, 0.1); padding: 5px 15px; border-radius: 10px;">300s</div>
</div>
<div style="display:flex; flex-wrap:wrap; padding:25px; gap:25px; max-width: 1300px; margin: auto;">
    <div style="flex:3; min-width:300px;">
        <form id="examForm" method="POST" action="/submit">
            {% for q in questions %}
            <div class="q-view" id="q-container-{{loop.index0}}">
                <span style="color:var(--primary); font-weight:700; background:rgba(79,70,229,0.1); padding:5px 10px; border-radius:8px;">Q #{{loop.index}} (+4, -1)</span>
                <p style="font-size: 1.25rem; min-height: 120px; line-height:1.7; margin-top:20px;">{{q.q}}</p>
                <div style="margin: 25px 0;">
                    <label class="option-row"><input type="radio" name="{{q.id}}" value="0" onclick="markAnswered({{loop.index0}})"> {{q.a}}</label>
                    <label class="option-row"><input type="radio" name="{{q.id}}" value="1" onclick="markAnswered({{loop.index0}})"> {{q.b}}</label>
                    <label class="option-row"><input type="radio" name="{{q.id}}" value="2" onclick="markAnswered({{loop.index0}})"> {{q.c}}</label>
                    <label class="option-row"><input type="radio" name="{{q.id}}" value="3" onclick="markAnswered({{loop.index0}})"> {{q.d}}</label>
                </div>
            </div>
            {% endfor %}
            <div style="margin-top:25px; display:flex; gap:15px;">
                <button type="button" onclick="saveNext()" style="flex:1; background:var(--primary); color:white; border:none; padding:16px; border-radius:14px; font-weight:bold; cursor:pointer; transition:0.3s;">Save & Next ➡️</button>
                <button type="button" onclick="markReview()" style="flex:1; background:var(--rev); color:white; border:none; padding:16px; border-radius:14px; font-weight:bold; cursor:pointer; transition:0.3s;">Review 🔖</button>
            </div>
        </form>
    </div>
    <div style="flex:1; background:var(--card-bg); padding:25px; border-radius:25px; height: fit-content; min-width:280px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05);">
        <p style="margin-top:0; font-weight:bold; color:#94a3b8; text-align:center;">Question Palette</p>
        <div class="palette-grid">
            {% for q in questions %}
            <div class="p-btn" id="p-btn-{{loop.index0}}" onclick="jumpTo({{loop.index0}})">{{loop.index}}</div>
            {% endfor %}
        </div>
        <button type="button" onclick="confirmSubmit()" style="width:100%; margin-top:30px; background:var(--ans); border:none; padding:18px; border-radius:15px; color:white; font-weight:bold; cursor:pointer; box-shadow: 0 5px 15px rgba(16,185,129,0.3); transition:0.3s; font-size:1.1rem;">Final Submit 🔥</button>
    </div>
</div>
<script>
    let currentIdx = 0; const totalQs = {{questions|length}}; 
    let status = Array(totalQs).fill('unvisited');

    function updateView() {
        document.querySelectorAll('.q-view').forEach((el, i) => el.classList.toggle('active', i === currentIdx));
        document.querySelectorAll('.p-btn').forEach((el, i) => el.classList.toggle('active', i === currentIdx));
        if(window.MathJax) MathJax.typeset();
    }

    function markAnswered(idx) {
        if(status[idx] !== 'answered-review') {
            status[idx] = 'answered';
            document.getElementById(`p-btn-${idx}`).className = 'p-btn answered';
        }
    }

    function saveNext() {
        if(status[currentIdx] === 'unvisited') {
            status[currentIdx] = 'not-answered';
            document.getElementById(`p-btn-${currentIdx}`).className = 'p-btn not-answered';
        }
        if(currentIdx < totalQs - 1) { currentIdx++; updateView(); }
    }

    function markReview() {
        let currentQElements = document.querySelectorAll('.q-view');
        let currentQ = currentQElements[currentIdx];
        let radioButtons = currentQ.querySelectorAll('input[type="radio"]');
        let hasAns = false;
        radioButtons.forEach(rb => { if(rb.checked) hasAns = true; });

        if(hasAns) {
            status[currentIdx] = 'answered-review';
            document.getElementById(`p-btn-${currentIdx}`).className = 'p-btn answered-review';
        } else {
            status[currentIdx] = 'review';
            document.getElementById(`p-btn-${currentIdx}`).className = 'p-btn review';
        }
        if(currentIdx < totalQs - 1) { currentIdx++; updateView(); }
    }

    function jumpTo(idx) {
        if(status[currentIdx] === 'unvisited' && idx !== currentIdx) {
            status[currentIdx] = 'not-answered';
            document.getElementById(`p-btn-${currentIdx}`).className = 'p-btn not-answered';
        }
        currentIdx = idx; updateView(); 
    }

    function confirmSubmit() { 
        if(confirm("soch ke akhri baar submit Krna hai ki nhi no. Km aaye to gand todenge ghr Wale 🤨")) {
            document.getElementById('examForm').submit(); 
        }
    }
    
    let t = 300; 
    let timerInterval = setInterval(() => { 
        t--; 
        document.getElementById('timer').innerText = t + "s"; 
        if(t <= 10) { document.getElementById('timer').style.background = 'rgba(239, 68, 68, 0.3)'; }
        if(t <= 0) { clearInterval(timerInterval); document.getElementById('examForm').submit(); }
    }, 1000);

    updateView();
</script>
'''

RESULT_HTML = COMMON_STYLE + '''
<div style="display:flex; align-items:center; justify-content:center; min-height:100vh; padding:25px;">
    <div class="glass-card" style="text-align:center; width:100%; max-width:550px; border-color:{{color}};">
        <h2 style="color:{{color}}; margin-bottom:5px;">Report Card 📊</h2>
        <img src="{{result_gif}}" alt="Result GIF" style="width:150px; border-radius:15px; margin: 15px 0; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
        <div style="font-size: 5rem; font-weight: 800; margin: 15px 0; text-shadow: 0 0 25px {{color}}; color:{{color}};">{{score}}</div>
        <p style="color:#94a3b8; margin-top:-10px; font-size:1.1rem;">Total Points / {{max}}</p>
        <div style="display:flex; justify-content: space-around; margin: 30px 0; padding:20px; background:rgba(0,0,0,0.3); border-radius:20px; border: 1px solid rgba(255,255,255,0.05);">
            <div style="color:var(--ans); font-size:1.1rem;"><b>{{c}}</b><br><small>Sahi ✅</small></div>
            <div style="color:var(--wrong); font-size:1.1rem;"><b>{{w}}</b><br><small>Galat ❌</small></div>
            <div style="color:#64748b; font-size:1.1rem;"><b>{{s}}</b><br><small>Khali ⚪</small></div>
        </div>
        <div style="background:rgba(255,255,255,0.03); padding:25px; border-radius:20px; border-left: 5px solid {{color}}; margin-bottom:25px; box-shadow: inset 0 0 10px rgba(0,0,0,0.2);">
            <p style="font-size: 1.3rem; line-height:1.5; margin:0; font-weight:500;">{{msg}}</p>
        </div>
        <a href="/logout" class="btn-primary" style="text-decoration:none; display:block; font-size:1.1rem;">Niklo Yahan Se 🚪</a>
    </div>
</div>
'''

# Render par database auto-create karne ke liye
with app.app_context():
    init_db()
    

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
