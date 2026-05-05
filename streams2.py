import streamlit as st
import requests
import pandas as pd

# =========================
# 🔗 API & Webhook URLs
# =========================
# Replace with your actual endpoints
API_URL = "http://localhost:8000/ask"
N8N_WEBHOOK_URL = "https://fayad11.app.n8n.cloud/webhook-test/f2001c2b-9f3b-4de5-8e52-03d2a517c375"  # Put your n8n Test webhook URL here

st.set_page_config(
    page_title="NileTel Support Assistant", layout="centered", page_icon="📡"
)

# Basic RTL layout for Arabic support
st.markdown(
    """
<style>
    body { direction: rtl; text-align: right; }
    .stTextInput > div > div > input { direction: rtl; text-align: right; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📡 NileTel Support Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize payload ID
if "webhook_id" not in st.session_state:
    st.session_state.webhook_id = 1

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


st.sidebar.header("👤 بيانات المستخدم")
user_email = st.sidebar.text_input("البريد الإلكتروني (Email)")
user_phone = st.sidebar.text_input("رقم الهاتف (Phone Number)")


def trigger_n8n_webhook(user_query, answer, needs_action, email, phone):
    """Sends data to n8n webhook to handle Jira/Google Sheets & Email via ngrok"""
    if N8N_WEBHOOK_URL == "YOUR_N8N_WEBHOOK_URL_HERE":
        st.warning("⚠️ N8N Webhook URL is missing! Please paste your URL from n8n.")
        return

    current_id = st.session_state.webhook_id
    payload = {
        "ID": current_id,
        "query": user_query,
        "answer": answer,
        "action": needs_action,
        "email": email,
        "phone": phone,
    }

    # Increment ID and reset after 300
    st.session_state.webhook_id += 1
    if st.session_state.webhook_id > 300:
        st.session_state.webhook_id = 1

    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            st.success("✅ Workflow Triggered! Issue logged & Email sent via n8n.")
        else:
            st.error(f"❌ Failed to trigger workflow: {response.status_code}")
    except Exception as e:
        st.error(f"❌ Error connecting to n8n webhook: {e}")


# =========================
# 💬 ASK QUESTION
# =========================

query = st.chat_input("اكتب سؤالك هنا...")

if query:
    # Add and render user query
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.spinner("جاري جلب الرد..."):
        try:
            # 1. Ask FastAPI Backend
            payload = {"query": query}
            response = requests.post(API_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "لا يوجد رد.")
                needs_action = data.get("needs_action", "NO")
                source = data.get("displayed_source", "غير معروف")

                # Add and render bot response
                bot_reply = f"{answer}\n\n📚 **المصدر:** {source}"
                st.session_state.messages.append(
                    {"role": "assistant", "content": bot_reply}
                )

                with st.chat_message("assistant"):
                    st.markdown(bot_reply)

                # 2. Trigger Action if required
                if needs_action == "YES":
                    if not user_email or not user_phone:
                        st.warning(
                            "⚠️ يرجى إدخال البريد الإلكتروني ورقم الهاتف في القائمة الجانبية لتسجيل الطلب."
                        )
                    else:
                        trigger_n8n_webhook(
                            query, answer, needs_action, user_email, user_phone
                        )
            else:
                st.error("حدث خطأ في الخادم.")

        except requests.exceptions.RequestException:
            st.error("❌ فشل الاتصال بالخادم الخلفي. تأكد من تشغيل `mains2.py`.")

            st.error("API error")

        except Exception as e:
            st.error(f"Connection error: {e}")

# =========================
# 🎫 SHOW TICKETS
# =========================
st.divider()
st.subheader("📋 Tickets")

if st.button("Load Tickets"):
    try:
        # Read the Google Sheet CSV into a DataFrame using the provided link
        sheet_url = "https://docs.google.com/spreadsheets/d/1BevevWL8Pbu4T7RbR1pKcbfKsYX9iATE2JNf5ptnw54/export?format=csv&gid=0"
        df = pd.read_csv(sheet_url)
        st.success("Tickets loaded successfully")

        # TODO: Display the DataFrame in Streamlit
        st.dataframe(df)

    except Exception as e:
        st.error(f"Failed to load tickets: {e}")
