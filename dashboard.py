from flask import Flask, render_template_string, redirect, request
from database import (
    get_pending_replies, get_pending_posts,
    approve_reply, deny_reply, approve_post, deny_post
)

app = Flask(__name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Ruckus Control Panel</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            background: #0a0a0a; 
            color: #eee; 
            font-family: 'Courier New', monospace; 
            padding: 30px;
        }
        h1 { 
            color: #ff6b00; 
            font-size: 1.8em; 
            margin-bottom: 5px;
        }
        .subtitle {
            color: #666;
            font-size: 0.85em;
            margin-bottom: 30px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat {
            background: #111;
            border: 1px solid #333;
            padding: 15px 25px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-number {
            font-size: 2em;
            color: #ff6b00;
            font-weight: bold;
        }
        .stat-label {
            font-size: 0.75em;
            color: #666;
            margin-top: 4px;
        }
        .section-title {
            color: #ff6b00;
            font-size: 1.1em;
            margin: 25px 0 15px 0;
            border-bottom: 1px solid #222;
            padding-bottom: 8px;
        }
        .card { 
            background: #111;
            border: 1px solid #2a2a2a; 
            padding: 20px; 
            margin: 12px 0; 
            border-radius: 8px;
            transition: border-color 0.2s;
        }
        .card:hover {
            border-color: #444;
        }
        .meta {
            color: #555;
            font-size: 0.78em;
            margin-bottom: 8px;
        }
        .username {
            color: #1d9bf0;
        }
        .original { 
            color: #aaa; 
            font-size: 0.9em; 
            margin-bottom: 12px;
            padding: 10px;
            background: #0d0d0d;
            border-radius: 5px;
            border-left: 3px solid #333;
        }
        .original-label {
            color: #555;
            font-size: 0.75em;
            margin-bottom: 4px;
        }
        textarea { 
            width: 100%; 
            background: #0d0d0d; 
            color: #fff; 
            border: 1px solid #333; 
            padding: 12px; 
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            border-radius: 5px;
            resize: vertical;
            min-height: 80px;
        }
        textarea:focus {
            outline: none;
            border-color: #ff6b00;
        }
        .char-count {
            color: #555;
            font-size: 0.75em;
            text-align: right;
            margin-top: 4px;
        }
        .char-count.over {
            color: #ff4444;
        }
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 12px;
        }
        .btn-approve { 
            background: #1a6b1a; 
            color: white; 
            padding: 8px 20px; 
            border: none; 
            cursor: pointer;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            transition: background 0.2s;
        }
        .btn-approve:hover { background: #228b22; }
        .btn-deny { 
            background: #6b1a1a; 
            color: white; 
            padding: 8px 20px; 
            border: none; 
            cursor: pointer;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            transition: background 0.2s;
        }
        .btn-deny:hover { background: #8b2222; }
        .empty {
            color: #444;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
        .badge {
            display: inline-block;
            background: #ff6b00;
            color: black;
            font-size: 0.7em;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: bold;
            margin-left: 8px;
            vertical-align: middle;
        }
    </style>
    <script>
        function updateCharCount(textarea, countId) {
            const len = textarea.value.length;
            const el = document.getElementById(countId);
            el.textContent = len + ' / 280 characters';
            if (len > 280) {
                el.classList.add('over');
            } else {
                el.classList.remove('over');
            }
        }
    </script>
</head>
<body>
    <h1>🎙️ RUCKUS CONTROL PANEL</h1>
    <p class="subtitle">Uncle Ruckus, no relation. Approve or deny before anything goes live.</p>

    <div class="stats">
        <div class="stat">
            <div class="stat-number">{{ pending_replies|length }}</div>
            <div class="stat-label">PENDING REPLIES</div>
        </div>
        <div class="stat">
            <div class="stat-number">{{ pending_posts|length }}</div>
            <div class="stat-label">PENDING POSTS</div>
        </div>
    </div>

    <!-- REPLY QUEUE -->
    <div class="section-title">
        💬 REPLY QUEUE
        {% if pending_replies|length > 0 %}
        <span class="badge">{{ pending_replies|length }}</span>
        {% endif %}
    </div>

    {% if pending_replies %}
        {% for r in pending_replies %}
        <div class="card">
            <div class="meta">
                <span class="username">@{{ r.username }}</span> · {{ r.created_at }}
            </div>
            <div class="original">
                <div class="original-label">THEY SAID:</div>
                {{ r.original_message }}
            </div>
            <form method="POST" action="/action/reply">
                <div class="original-label" style="margin-bottom: 6px;">RUCKUS WANTS TO SAY:</div>
                <textarea 
                    name="edited_reply" 
                    id="reply_{{ r.id }}"
                    oninput="updateCharCount(this, 'count_{{ r.id }}')"
                >{{ r.proposed_reply }}</textarea>
                <div class="char-count" id="count_{{ r.id }}">
                    {{ r.proposed_reply|length }} / 280 characters
                </div>
                <input type="hidden" name="id" value="{{ r.id }}">
                <div class="actions">
                    <button class="btn-approve" name="action" value="approved">✅ Approve</button>
                    <button class="btn-deny" name="action" value="denied">❌ Deny</button>
                </div>
            </form>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty">No pending replies. Ruckus is resting.</div>
    {% endif %}

    <!-- POST QUEUE -->
    <div class="section-title" style="margin-top: 40px;">
        📢 UNPROMPTED POST QUEUE
        {% if pending_posts|length > 0 %}
        <span class="badge">{{ pending_posts|length }}</span>
        {% endif %}
    </div>

    {% if pending_posts %}
        {% for p in pending_posts %}
        <div class="card">
            <div class="meta">Generated · {{ p.created_at }}</div>
            <form method="POST" action="/action/post">
                <div class="original-label" style="margin-bottom: 6px;">RUCKUS WANTS TO POST:</div>
                <textarea 
                    name="edited_content"
                    id="post_{{ p.id }}"
                    oninput="updateCharCount(this, 'pcount_{{ p.id }}')"
                    rows="4"
                >{{ p.content }}</textarea>
                <div class="char-count" id="pcount_{{ p.id }}">
                    {{ p.content|length }} / 280 characters
                </div>
                <input type="hidden" name="id" value="{{ p.id }}">
                <div class="actions">
                    <button class="btn-approve" name="action" value="approved">✅ Approve</button>
                    <button class="btn-deny" name="action" value="denied">❌ Deny</button>
                </div>
            </form>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty">No pending posts.</div>
    {% endif %}

</body>
</html>
"""

@app.route("/")
def dashboard():
    pending_replies = get_pending_replies()
    pending_posts = get_pending_posts()
    return render_template_string(
        DASHBOARD_HTML,
        pending_replies=pending_replies,
        pending_posts=pending_posts
    )

@app.route("/action/reply", methods=["POST"])
def action_reply():
    id = request.form["id"]
    action = request.form["action"]
    edited_reply = request.form["edited_reply"]
    if action == "approved":
        approve_reply(id, edited_reply)
    else:
        deny_reply(id)
    return redirect("/")

@app.route("/action/post", methods=["POST"])
def action_post():
    id = request.form["id"]
    action = request.form["action"]
    edited_content = request.form["edited_content"]
    if action == "approved":
        approve_post(id, edited_content)
    else:
        deny_post(id)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, port=5000)