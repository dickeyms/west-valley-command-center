import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
 
# --- PASSWORD PROTECTION ---
def check_password():
    """Returns True if the user has entered the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["passwords"]["auth"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- CONFIGURATION ---
API_URL = "https://wvm.instructure.com"

# List of students to monitor
STUDENTS = [
    "DavidS", "Jonathan", "DavidM", "Anirudh", "Alex",
    "Jesus", "Olivia", "Angel", "Tava", "Heidy", "Melody"
]

# --- MAIN APPLICATION ---
st.set_page_config(page_title="West Valley Command Center", layout="wide")
st.title("⚡ West Valley Command Center")

# --- DATE FILTERING LOGIC ---
st.subheader("📅 Timeframe")
col1, col2 = st.columns([1, 3])

with col1:
    # User selects the range
    time_option = st.radio(
        "Show tasks due by:",
        ["End of This Week", "End of Next Week (2 Weeks)", "3 Weeks Out", "All Tasks"],
        index=0  # Defaults to "End of This Week"
    )

# Calculate the specific cutoff date
today = datetime.now()
# 6 is Sunday. Calculate days remaining until Sunday.
days_until_sunday = 6 - today.weekday()
if days_until_sunday < 0:
    days_until_sunday += 7
this_coming_sunday = today + timedelta(days=days_until_sunday)

if "This Week" in time_option:
    end_date = this_coming_sunday
elif "2 Weeks" in time_option:
    end_date = this_coming_sunday + timedelta(weeks=1)
elif "3 Weeks" in time_option:
    end_date = this_coming_sunday + timedelta(weeks=2)
else:
    end_date = None  # No filter for "All Tasks"

# Display the exact date range being checked
if end_date:
    st.caption(f"Showing assignments due before: **{end_date.strftime('%A, %b %d')}**")
else:
    st.caption("Showing **everything** on the planner.")


def get_student_todo(name, token, cutoff_date=None):
    """Fetches To-Do list using the DIRECT Canvas API endpoint"""
    try:
        url = f"{API_URL}/api/v1/planner/items"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        params = {
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "filter": "new_activity",
            "per_page": 50,
            "order": "asc"  # Sort by due date
        }

        # If we have a cutoff date, add it to the API params
        if cutoff_date:
            params["end_date"] = cutoff_date.strftime("%Y-%m-%d")

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            st.error(f"⚠️ {name}: Access Denied (Check Token)")
            return []

        items = response.json()

        tasks = []
        for item in items:
            title = item.get('plannable', {}).get('title', 'Untitled')
            due_date_str = item.get('plannable_date', None)

            # Check Status
            status = "Todo"
            score = ""

            if 'submissions' in item:
                subs = item['submissions']
                if isinstance(subs, dict):
                    if subs.get('submitted'):
                        status = "Submitted"
                    if subs.get('graded'):
                        score = f" (Score: {subs.get('score')})"
                elif isinstance(subs, list) and len(subs) > 0:
                    if subs[0].get('submitted'):
                        status = "Submitted"

            # Format Date
            if due_date_str:
                dt = pd.to_datetime(due_date_str)
                formatted_date = dt.strftime('%m-%d %H:%M')
            else:
                formatted_date = "No Date"

            tasks.append({
                "Student": name,
                "Task": title,
                "Due": formatted_date,
                "Status": status + score
            })

        return tasks

    except Exception as e:
        print(f"DEBUG ERROR for {name}: {e}")
        return []


# --- MAIN DASHBOARD UI ---

if st.button("🔄 Sync All Students"):
    all_data = []

    progress_bar = st.progress(0)

    for i, student_name in enumerate(STUDENTS):
        # Get token from secrets
        try:
            token = st.secrets["tokens"][student_name]
        except KeyError:
            st.warning(f"⚠️ Token not found for {student_name} in secrets")
            progress_bar.progress((i + 1) / len(STUDENTS))
            continue

        # Pass the calculated end_date to the function
        student_tasks = get_student_todo(student_name, token, end_date)
        all_data.extend(student_tasks)
        progress_bar.progress((i + 1) / len(STUDENTS))

    progress_bar.empty()

    if all_data:
        df = pd.DataFrame(all_data)

        st.subheader("📋 Master List")
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn(
                    "Status",
                    validate="^Submitted"
                )
            }
        )

        st.divider()
        st.subheader("👤 Student Breakdown")

        cols = st.columns(3)
        unique_students = df['Student'].unique()

        for i, student in enumerate(unique_students):
            col = cols[i % 3]
            student_work = df[df['Student'] == student]

            with col:
                with st.container(border=True):
                    st.write(f"**{student}**")
                    st.table(student_work[['Task', 'Status', 'Due']])
    else:
        st.success("🎉 No active assignments found for this time period!")
