import streamlit as st
import os.path
import json
import html
from openai import OpenAI
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- CONFIGURATION & CUSTOM CSS ---
st.set_page_config(page_title="Teacher's Command Center", page_icon="🍎", layout="wide")

st.markdown("""
<style>
    /* 1. BACKGROUND */
    .stApp {
        background-color: #f4f6f9;
    }
    
    /* 2. TOP BANNER */
    .banner-container {
        background-color: #1c2c52;
        padding: 40px 20px 25px 20px;
        border-top-left-radius: 15px;
        border-top-right-radius: 15px;
        border-bottom-left-radius: 0px;
        border-bottom-right-radius: 0px;
        color: white;
        text-align: center;
    }
    .banner-container h1 {
        color: white;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
    }
    .banner-container p {
        color: #cfd8dc;
        font-size: 1.2rem;
        margin-top: 5px;
        margin-bottom: 0px;
    }
    
    /* 3. BUTTON (Glued to Banner) */
    div.stButton {
        margin-top: -1px; 
    }
    div.stButton > button {
        background-color: #1c2c52 !important;
        color: white !important;
        border: none !important;
        border-top: 1px solid #34495e; 
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 15px;
        border-bottom-right-radius: 15px;
        font-weight: 800;
        font-size: 1.2rem;
        padding: 15px 0px;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 2px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: background-color 0.3s;
    }
    div.stButton > button:hover {
        background-color: #2a4075 !important;
    }

    /* 4. CARDS */
    .metric-card {
        border-radius: 15px;
        padding: 20px;
        height: 400px;
        overflow-y: auto;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        color: #1c2c52;
        margin-top: 20px;
    }
    .card-blue { background-color: #96ccf5; }
    .card-pink { background-color: #ed74b2; color: white; }
    
    .card-header {
        font-size: 1.4rem;
        font-weight: 900;
        margin-bottom: 15px;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    /* 5. BOTTOM SECTION */
    .section-header {
        background: linear-gradient(90deg, #2755a2 0%, #488cc8 50%, #da76b4 100%);
        color: white;
        padding: 15px;
        border-top-left-radius: 15px;
        border-top-right-radius: 15px;
        font-size: 1.5rem;
        font-weight: 800;
        text-align: center;
        margin-top: 40px;
    }
    .section-content {
        background-color: white;
        padding: 30px;
        border-bottom-left-radius: 15px;
        border-bottom-right-radius: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    /* HOT TAKE ITEMS */
    .hot-take-item {
        border-bottom: 1px solid #eee;
        padding-bottom: 20px;
        margin-bottom: 20px;
    }
    .hot-take-title {
        color: #1c2c52;
        font-size: 1.3rem;
        font-weight: 900;
        display: block;
        margin-bottom: 5px;
    }
    .hot-take-meta {
        font-size: 1rem;
        color: #555;
        margin-bottom: 8px;
        display: block;
    }
    .crucial-badge {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.9rem;
    }

    /* DRAFT STYLES */
    .draft-wrapper {
        margin-bottom: 30px;
    }
    .draft-label {
        color: #1c2c52;
        font-weight: 800;
        font-size: 1.1rem;
        margin-bottom: 5px;
        display: block;
        margin-top: 10px;
    }
    .draft-block {
        background-color: #f8f9fa;
        border-left: 5px solid #1c2c52;
        padding: 20px;
        font-family: sans-serif; /* Normal font for reading */
        color: #333;
        white-space: pre-wrap; /* Preserves line breaks in the email */
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# --- GOOGLE AUTHENTICATION ---
def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                st.error("Missing 'credentials.json'! Please upload it to your files.")
                st.stop()
            # NOTE: This flow only works locally. For cloud deployment, you usually need token.json uploaded
            # or a more advanced secrets configuration.
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def fetch_emails(service):
    query = 'newer_than:1d' 
    results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
    messages = results.get('messages', [])
    email_data = []
    if not messages: return []
    
    for msg in messages:
        try:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = txt['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
            snippet = txt.get('snippet', '')
            email_data.append(f"From: {sender} | Subject: {subject} | Body: {snippet}")
        except: pass
    return email_data

def clean_text(text):
    """Helper to escape HTML characters so <email@addresses> don't break the app."""
    if not text: return ""
    return html.escape(str(text))

# --- OPENAI "BRAIN" ---
def generate_briefing(email_list, api_key):
    if not email_list: return None
    client = OpenAI(api_key=api_key)

    system_instruction = """
    You are an executive assistant. Analyze emails from the last 24h.
    Return STRICT JSON with these 5 keys:
    
    1. "schedule": Array of strings (Calendar events).
    2. "actions": Array of strings (Top 5 tasks).
    3. "traffic": Object {"total": int, "new": int, "continuing": int}.
    
    4. "hot_takes": Array of objects (Top 5 urgent emails). 
       Format: {"subject": "...", "sender": "...", "summary": "...", "crucial_note": "..."}
       
    5. "drafts": Array of strings (5 full email drafts). 
       IMPORTANT: Write the ACTUAL complete email response for each hot take.
       Start with "Dear [Name]," and end with "Best regards,".
       Do not describe the email; actually write it.

    Anonymize student names.
    """
    
    user_message = "EMAILS:\n" + "\n".join(email_list)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"}, 
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_message}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error connecting to OpenAI: {e}")
        return None

# --- UI LAYOUT ---

# BANNER
st.markdown('<div class="banner-container"><h1>🚀 Teacher\'s Command Center</h1><p>Daily Intelligence & Action Plan</p></div>', unsafe_allow_html=True)

# BUTTON
if st.button("RUN DAILY ANALYSIS", type="primary", use_container_width=True):
    
    # 1. RETRIEVE KEY FROM SECRETS (Option 1)
    # This looks for the key in your "Advanced Settings" on the deploy page
    try:
        user_api_key = st.secrets["OPENAI_API_KEY"]
    except:
        st.error("🚨 API Key not found! Please add `OPENAI_API_KEY` to the Secrets in Advanced Settings.")
        st.stop()

    if user_api_key:
        service = get_gmail_service()
        if service:
            with st.spinner('Accessing secure communications...'):
                emails = fetch_emails(service)
            
            if not emails:
                st.info("No emails found.")
            else:
                data = generate_briefing(emails, user_api_key)
                if data:
                    
                    # --- BUILD HTML STRINGS (NO INDENTATION TO FIX DISPLAY BUG) ---
                    
                    # Schedule
                    sched_items = [f"• {clean_text(item)}" for item in data.get('schedule', [])]
                    sched_html = "<br><br>".join(sched_items)
                    
                    # Actions
                    act_items = [f"☐ {clean_text(item)}" for item in data.get('actions', [])]
                    act_html = "<br><br>".join(act_items)
                    
                    # Traffic
                    stats = data.get('traffic', {})
                    traf_html = f"<b>Total:</b> {stats.get('total',0)}<br><br><b>New Threads:</b> {stats.get('new',0)}<br><br><b>Replies:</b> {stats.get('continuing',0)}"
                    
                    # Hot Takes Loop
                    hot_html = ""
                    hot_list = data.get('hot_takes', [])
                    for i, item in enumerate(hot_list):
                        s_subj = clean_text(item.get('subject'))
                        s_send = clean_text(item.get('sender'))
                        s_summ = clean_text(item.get('summary'))
                        s_note = clean_text(item.get('crucial_note'))
                        
                        hot_html += f"""<div class="hot-take-item">
<span class="hot-take-title">🔥 {i+1}. {s_subj}</span>
<span class="hot-take-meta"><b>From:</b> {s_send}</span>
<span class="hot-take-meta">{s_summ}</span>
<span class="crucial-badge">Crucial Note: {s_note}</span>
</div>"""
                    
                    # Drafts Loop
                    draft_html = ""
                    draft_list = data.get('drafts', [])
                    for i, d in enumerate(draft_list):
                         subject_ref = "Email Response"
                         if i < len(hot_list):
                             subject_ref = clean_text(hot_list[i].get('subject'))
                         
                         clean_draft = clean_text(d)
                         
                         draft_html += f"""<div class="draft-wrapper">
<span class="draft-label">Draft for: "{subject_ref}"</span>
<div class="draft-block">{clean_draft}</div>
</div>"""

                    # --- RENDER UI ---
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f'<div class="metric-card card-blue"><div class="card-header">📅 Schedule</div>{sched_html}</div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="metric-card card-pink"><div class="card-header">✅ Action Items</div>{act_html}</div>', unsafe_allow_html=True)
                    with col3:
                        st.markdown(f'<div class="metric-card card-blue"><div class="card-header">📊 Traffic</div>{traf_html}</div>', unsafe_allow_html=True)

                    # Bottom Section
                    st.markdown('<div class="section-header">Technological Onboarding Assistant</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="section-content">
                        <h3 style="color:#1c2c52; font-weight:900; margin-bottom:20px;">🔥 Hot Take Emails (Top 5)</h3>
                        {hot_html}
                        <h3 style="color:#1c2c52; font-weight:900; margin-top:40px; border-top:1px solid #eee; padding-top:20px;">✍️ Draft Responses</h3>
                        {draft_html}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown('<div style="text-align:center; color:#888; margin-top:20px;">© 2025 School Technology Department</div>', unsafe_allow_html=True)
