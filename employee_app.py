import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Employee Ticket Dashboard", layout="wide", page_icon="👨‍💻"
)

st.title("👨‍💻 Employee Ticket Dashboard")
st.markdown("View and update active customer support tickets.")

# Google Sheet CSV export link (using the same link from your other app)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1BevevWL8Pbu4T7RbR1pKcbfKsYX9iATE2JNf5ptnw54/export?format=csv&gid=0"


@st.cache_data(ttl=60)
def load_tickets():
    try:
        df = pd.read_csv(SHEET_URL)
        return df
    except Exception as e:
        st.error(f"Failed to load tickets: {e}")
        return pd.DataFrame()


df = load_tickets()

if not df.empty:
    st.subheader("Active Tickets")

    # Filter tickets
    status_filter = st.selectbox(
        "Filter by Status",
        ["All"] + list(df.get("Status", pd.Series(["Open", "Closed"])).unique()),
    )

    display_df = df if status_filter == "All" else df[df["Status"] == status_filter]

    st.dataframe(display_df, use_container_width=True)

    st.divider()
    st.subheader("Update Ticket Status")

    # Simple form to update ticket (Note: updating Google Sheets requires a webhook or Google Sheets API)
    with st.form("update_ticket_form"):
        # Use appropriate ID column based on your sheet
        ticket_id = st.text_input("Enter Ticket ID to close/update")
        resolution = st.text_area("Resolution / Notes")
        status = st.selectbox("New Status", ["Closed", "In Progress", "Escalated"])

        submitted = st.form_submit_button("Update Ticket")
        if submitted:
            if ticket_id:
                # Here you would typically send a request to a backend API or webhook (like n8n)
                # to update the corresponding row in Google Sheets/Jira.
                st.success(
                    f"✅ Ticket {ticket_id} marked as {status}! (Note: Connect to a webhook/API to make this persistent)"
                )
            else:
                st.error("Please enter a Ticket ID")
else:
    st.info("No tickets to display or waiting for CSV data.")
