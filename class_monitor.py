import streamlit as st
import pandas as pd
import requests
import re
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
st.set_page_config(page_title="Camden-West Valley Canvas Monitoring Tool", layout="wide")

# Custom CSS for Newsreader font
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:wght@400;600;700&display=swap" rel="stylesheet">
<style>
    .title-text {
        font-family: 'Newsreader', serif;
        font-size: 3rem;
        font-weight: 600;
        line-height: 1.2;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Custom title with logo
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.image("https://www.westvalley.edu/community-grant/_files/community-grant.jpg", width=120)
with col_title:
    st.markdown('<div class="title-text">Camden-West Valley Canvas Monitoring Tool</div>', unsafe_allow_html=True)

# --- STUDENT SELECTION ---
st.subheader("👥 Student Selection")
col1, col2 = st.columns([1, 3])

with col1:
    selection_mode = st.radio(
        "Select students:",
        ["All Students", "Individual Students"],
        index=0
    )

with col2:
    selected_students = []
    if selection_mode == "All Students":
        selected_students = STUDENTS
        st.info(f"📊 Monitoring all {len(STUDENTS)} students")
    elif selection_mode == "Individual Students":
        selected_students = st.multiselect(
            "Choose students to monitor:",
            STUDENTS,
            default=STUDENTS[:3]  # Default to first 3 students
        )

if not selected_students:
    st.warning("⚠️ Please select at least one student to monitor")
    st.stop()


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


def get_student_courses(name, token):
    """Fetches active courses for a student - prerequisite for grades and announcements"""
    try:
        url = f"{API_URL}/api/v1/courses"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        params = {
            "enrollment_type": "student",
            "enrollment_state": "active",
            "per_page": 100
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            st.error(f"⚠️ {name}: Unable to fetch courses (Check Token)")
            return []

        courses_data = response.json()

        # Extract relevant course information
        courses = []
        for course in courses_data:
            courses.append({
                "id": course.get('id'),
                "name": course.get('name', 'Unknown Course'),
                "course_code": course.get('course_code', '')
            })

        return courses

    except Exception as e:
        print(f"DEBUG ERROR fetching courses for {name}: {e}")
        return []


def strip_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.sub('<.*?>', '', text)
    return clean.strip()


def get_student_conversations(name, token):
    """Fetches unread conversations (emails) from Canvas - last 3 weeks"""
    try:
        url = f"{API_URL}/api/v1/conversations"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        params = {
            "scope": "unread",
            "per_page": 100  # Increased to get more results
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            st.error(f"⚠️ {name}: Unable to fetch conversations (Check Token)")
            return []

        conversations = response.json()

        # Filter to last 3 weeks
        three_weeks_ago = datetime.now() - timedelta(weeks=3)

        messages = []
        for convo in conversations:
            last_message_at = convo.get('last_message_at')

            # Only include messages from last 3 weeks
            if last_message_at:
                msg_date = pd.to_datetime(last_message_at)
                if msg_date < three_weeks_ago:
                    continue
            else:
                continue  # Skip if no date

            subject = convo.get('subject', 'No Subject')
            last_message = convo.get('last_message', '')

            # Create preview (first 100 chars)
            preview = strip_html(last_message)
            if len(preview) > 100:
                preview = preview[:100] + "..."

            # Get sender info
            participants = convo.get('participants', [])
            from_user = "Unknown"
            if participants:
                from_user = participants[0].get('name', 'Unknown')

            messages.append({
                "Student": name,
                "Subject": subject,
                "Preview": preview,
                "Date": last_message_at,  # Store as datetime for sorting
                "Date_Formatted": pd.to_datetime(last_message_at).strftime('%m-%d %H:%M'),
                "From": from_user
            })

        return messages

    except Exception as e:
        print(f"DEBUG ERROR fetching conversations for {name}: {e}")
        return []


def get_student_announcements(name, token, courses):
    """Fetches announcements from all student courses - last 3 weeks"""
    try:
        if not courses:
            return []

        url = f"{API_URL}/api/v1/announcements"

        headers = {
            "Authorization": f"Bearer {token}"
        }

        # Build context_codes array from course IDs
        context_codes = [f"course_{course['id']}" for course in courses]

        # Calculate start date (3 weeks ago) and end date (today)
        three_weeks_ago = datetime.now() - timedelta(weeks=3)

        params = {
            "context_codes[]": context_codes,
            "active_only": True,
            "start_date": three_weeks_ago.strftime("%Y-%m-%d"),
            "end_date": datetime.now().strftime("%Y-%m-%d"),
            "per_page": 100
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            st.error(f"⚠️ {name}: Unable to fetch announcements (Check Token)")
            return []

        announcements_data = response.json()

        announcements = []
        for announcement in announcements_data:
            title = announcement.get('title', 'No Title')
            message = announcement.get('message', '')
            posted_at = announcement.get('posted_at')

            if not posted_at:
                continue

            # Strip HTML and create preview
            preview = strip_html(message)
            if len(preview) > 150:
                preview = preview[:150] + "..."

            # Get course name from context_code
            context_code = announcement.get('context_code', '')
            course_name = "Unknown Course"
            if context_code.startswith('course_'):
                course_id = int(context_code.replace('course_', ''))
                for course in courses:
                    if course['id'] == course_id:
                        course_name = course['name']
                        break

            announcements.append({
                "Student": name,
                "Title": title,
                "Preview": preview,
                "Posted": posted_at,  # Store as datetime for sorting
                "Posted_Formatted": pd.to_datetime(posted_at).strftime('%m-%d'),
                "Course": course_name
            })

        return announcements

    except Exception as e:
        print(f"DEBUG ERROR fetching announcements for {name}: {e}")
        return []


def get_student_grades(name, token, courses):
    """Fetches submissions and flags missing/zero grades"""
    grade_issues = []

    try:
        headers = {
            "Authorization": f"Bearer {token}"
        }

        # Iterate through each course
        for course in courses:
            course_id = course['id']
            course_name = course['name']

            try:
                url = f"{API_URL}/api/v1/courses/{course_id}/students/submissions"
                params = {
                    "student_ids[]": "all",
                    "per_page": 100
                }

                response = requests.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    continue  # Skip this course if we can't access submissions

                submissions = response.json()

                # Check each submission for issues
                for submission in submissions:
                    # Skip if excused
                    if submission.get('excused'):
                        continue

                    assignment_name = submission.get('assignment', {}).get('name', 'Unknown Assignment')
                    score = submission.get('score')
                    missing = submission.get('missing', False)
                    workflow_state = submission.get('workflow_state', '')
                    due_at = submission.get('assignment', {}).get('due_at')

                    issue = None

                    # Check for zero grade (but not excused)
                    if score == 0 and not submission.get('excused'):
                        issue = "Zero Grade"
                    # Check for missing flag
                    elif missing:
                        issue = "Missing"
                    # Check for unsubmitted past due
                    elif workflow_state == "unsubmitted" and due_at:
                        due_date = pd.to_datetime(due_at)
                        if due_date < datetime.now():
                            issue = "Unsubmitted"

                    # If we found an issue, add it to the list
                    if issue:
                        formatted_due = "No Date"
                        if due_at:
                            dt = pd.to_datetime(due_at)
                            formatted_due = dt.strftime('%m-%d')

                        grade_issues.append({
                            "Student": name,
                            "Assignment": assignment_name,
                            "Course": course_name,
                            "Issue": issue,
                            "Due Date": formatted_due,
                            "Status": workflow_state
                        })

            except Exception as e:
                print(f"DEBUG ERROR fetching submissions for {name} in course {course_id}: {e}")
                continue  # Skip this course and continue with others

        return grade_issues

    except Exception as e:
        print(f"DEBUG ERROR in get_student_grades for {name}: {e}")
        return []


# --- MAIN DASHBOARD UI ---

# Initialize session state for data persistence
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.grades_df = None
    st.session_state.convos_df = None
    st.session_state.announcements_df = None
    st.session_state.todos_df = None

if st.button("🔄 Sync Selected Students"):
    # Initialize collectors for all data types
    all_conversations = []
    all_todos = []
    all_grades = []
    all_announcements = []

    progress_bar = st.progress(0)

    for i, student_name in enumerate(selected_students):
        # Get token from secrets
        try:
            token = st.secrets["tokens"][student_name]
        except KeyError:
            st.warning(f"⚠️ Token not found for {student_name} in secrets")
            progress_bar.progress((i + 1) / len(selected_students))
            continue

        # 1. Get courses (needed for grades & announcements)
        courses = get_student_courses(student_name, token)

        # 2. Fetch all data types
        student_convos = get_student_conversations(student_name, token)
        student_todos = get_student_todo(student_name, token, None)  # Will add filtering in UI
        student_grades = get_student_grades(student_name, token, courses)
        student_announcements = get_student_announcements(student_name, token, courses)

        # 3. Collect results
        all_conversations.extend(student_convos)
        all_todos.extend(student_todos)
        all_grades.extend(student_grades)
        all_announcements.extend(student_announcements)

        progress_bar.progress((i + 1) / len(selected_students))

    progress_bar.empty()

    # Convert to DataFrames
    grades_df = pd.DataFrame(all_grades) if all_grades else None
    convos_df = pd.DataFrame(all_conversations) if all_conversations else None
    announcements_df = pd.DataFrame(all_announcements) if all_announcements else None
    todos_df = pd.DataFrame(all_todos) if all_todos else None

    # Sort conversations and announcements by date (newest first)
    if convos_df is not None and not convos_df.empty:
        convos_df['Date'] = pd.to_datetime(convos_df['Date'])
        convos_df = convos_df.sort_values('Date', ascending=False)

    if announcements_df is not None and not announcements_df.empty:
        announcements_df['Posted'] = pd.to_datetime(announcements_df['Posted'])
        announcements_df = announcements_df.sort_values('Posted', ascending=False)

    # Store in session state
    st.session_state.grades_df = grades_df
    st.session_state.convos_df = convos_df
    st.session_state.announcements_df = announcements_df
    st.session_state.todos_df = todos_df
    st.session_state.data_loaded = True

# Retrieve data from session state
if st.session_state.data_loaded:
    grades_df = st.session_state.grades_df
    convos_df = st.session_state.convos_df
    announcements_df = st.session_state.announcements_df
    todos_df = st.session_state.todos_df
else:
    grades_df = None
    convos_df = None
    announcements_df = None
    todos_df = None

if st.session_state.data_loaded:
    # --- GRADES ALERTS SECTION ---
    grades_count = len(grades_df) if grades_df is not None and not grades_df.empty else 0
    with st.expander(f"🚨 GRADES ALERTS ({grades_count})", expanded=(grades_count > 0)):
        if grades_df is not None and not grades_df.empty:
            st.subheader("📋 Master Alert List")
            st.dataframe(grades_df, use_container_width=True)

            st.divider()
            st.subheader("👤 Student Breakdown")

            cols = st.columns(3)
            unique_students = grades_df['Student'].unique()

            for i, student in enumerate(unique_students):
                col = cols[i % 3]
                student_data = grades_df[grades_df['Student'] == student]

                with col:
                    with st.container(border=True):
                        st.write(f"**{student}**")
                        st.table(student_data[['Assignment', 'Issue', 'Due Date']])
        else:
            st.success("✅ No grade issues found!")

    # --- UNREAD MESSAGES SECTION ---
    convos_count = len(convos_df) if convos_df is not None and not convos_df.empty else 0
    with st.expander(f"📧 UNREAD MESSAGES ({convos_count})", expanded=False):
        if convos_df is not None and not convos_df.empty:
            # Add time filter for emails
            email_filter = st.radio(
                "Show emails from:",
                ["Last 3 Days", "Last Week", "Last 2 Weeks", "Last 3 Weeks (All)"],
                index=3,
                horizontal=True,
                key="email_filter"
            )

            # Apply time filter
            filtered_convos = convos_df.copy()
            if email_filter == "Last 3 Days":
                cutoff = datetime.now() - timedelta(days=3)
                filtered_convos = filtered_convos[filtered_convos['Date'] >= cutoff]
            elif email_filter == "Last Week":
                cutoff = datetime.now() - timedelta(weeks=1)
                filtered_convos = filtered_convos[filtered_convos['Date'] >= cutoff]
            elif email_filter == "Last 2 Weeks":
                cutoff = datetime.now() - timedelta(weeks=2)
                filtered_convos = filtered_convos[filtered_convos['Date'] >= cutoff]

            if not filtered_convos.empty:
                st.subheader("📋 Master Message List")
                # Display with formatted date
                display_convos = filtered_convos.copy()
                display_convos['Date'] = display_convos['Date_Formatted']
                st.dataframe(display_convos[['Student', 'Subject', 'Preview', 'Date', 'From']], use_container_width=True)

                st.divider()
                st.subheader("👤 Student Breakdown")

                cols = st.columns(3)
                unique_students = filtered_convos['Student'].unique()

                for i, student in enumerate(unique_students):
                    col = cols[i % 3]
                    student_data = filtered_convos[filtered_convos['Student'] == student].copy()
                    student_data['Date'] = student_data['Date_Formatted']

                    with col:
                        with st.container(border=True):
                            st.write(f"**{student}**")
                            st.table(student_data[['Subject', 'Preview', 'Date']])
            else:
                st.info(f"📬 No unread messages in the selected timeframe.")
        else:
            st.info("📬 All caught up! No unread messages.")

    # --- ANNOUNCEMENTS SECTION ---
    announcements_count = len(announcements_df) if announcements_df is not None and not announcements_df.empty else 0
    with st.expander(f"📢 ANNOUNCEMENTS ({announcements_count})", expanded=False):
        if announcements_df is not None and not announcements_df.empty:
            # Add time filter for announcements
            announcement_filter = st.radio(
                "Show announcements from:",
                ["Last 3 Days", "Last Week", "Last 2 Weeks", "Last 3 Weeks (All)"],
                index=3,
                horizontal=True,
                key="announcement_filter"
            )

            # Apply time filter
            filtered_announcements = announcements_df.copy()
            if announcement_filter == "Last 3 Days":
                cutoff = datetime.now() - timedelta(days=3)
                filtered_announcements = filtered_announcements[filtered_announcements['Posted'] >= cutoff]
            elif announcement_filter == "Last Week":
                cutoff = datetime.now() - timedelta(weeks=1)
                filtered_announcements = filtered_announcements[filtered_announcements['Posted'] >= cutoff]
            elif announcement_filter == "Last 2 Weeks":
                cutoff = datetime.now() - timedelta(weeks=2)
                filtered_announcements = filtered_announcements[filtered_announcements['Posted'] >= cutoff]

            if not filtered_announcements.empty:
                st.subheader("📋 Master Announcements List")
                # Display with formatted date
                display_announcements = filtered_announcements.copy()
                display_announcements['Posted'] = display_announcements['Posted_Formatted']
                st.dataframe(display_announcements[['Student', 'Title', 'Preview', 'Posted', 'Course']], use_container_width=True)

                st.divider()
                st.subheader("👤 Student Breakdown")

                cols = st.columns(3)
                unique_students = filtered_announcements['Student'].unique()

                for i, student in enumerate(unique_students):
                    col = cols[i % 3]
                    student_data = filtered_announcements[filtered_announcements['Student'] == student].copy()
                    student_data['Posted'] = student_data['Posted_Formatted']

                    with col:
                        with st.container(border=True):
                            st.write(f"**{student}**")
                            st.table(student_data[['Title', 'Preview', 'Posted']])
            else:
                st.info(f"📢 No announcements in the selected timeframe.")
        else:
            st.info("📢 No announcements in this timeframe.")

    # --- ASSIGNMENTS SECTION ---
    todos_count = len(todos_df) if todos_df is not None and not todos_df.empty else 0
    with st.expander(f"✅ ASSIGNMENTS ({todos_count})", expanded=True):
        if todos_df is not None and not todos_df.empty:
            # Add time filter for assignments
            assignment_filter = st.radio(
                "Show assignments due:",
                ["This Week", "Next Week", "Next 2 Weeks", "Next 3 Weeks", "All Upcoming"],
                index=2,
                horizontal=True,
                key="assignment_filter"
            )

            # Calculate cutoff date based on filter
            today = datetime.now()
            days_until_sunday = 6 - today.weekday()
            if days_until_sunday < 0:
                days_until_sunday += 7
            this_sunday = today + timedelta(days=days_until_sunday)

            if assignment_filter == "This Week":
                cutoff_date = this_sunday
            elif assignment_filter == "Next Week":
                cutoff_date = this_sunday + timedelta(weeks=1)
            elif assignment_filter == "Next 2 Weeks":
                cutoff_date = this_sunday + timedelta(weeks=2)
            elif assignment_filter == "Next 3 Weeks":
                cutoff_date = this_sunday + timedelta(weeks=3)
            else:
                cutoff_date = None

            # Apply filter to assignments
            filtered_todos = todos_df.copy()
            if cutoff_date:
                # Parse Due dates and filter
                filtered_todos['Due_Parsed'] = pd.to_datetime(filtered_todos['Due'], format='%m-%d %H:%M', errors='coerce')
                # Add current year for comparison
                current_year = datetime.now().year
                filtered_todos['Due_Parsed'] = filtered_todos['Due_Parsed'].apply(
                    lambda x: x.replace(year=current_year) if pd.notna(x) else x
                )
                filtered_todos = filtered_todos[
                    (filtered_todos['Due_Parsed'].isna()) |
                    (filtered_todos['Due_Parsed'] <= cutoff_date)
                ]

            if not filtered_todos.empty:
                st.caption(f"Showing {len(filtered_todos)} assignment(s)")
                st.subheader("📋 Master List")
                st.dataframe(
                    filtered_todos[['Student', 'Task', 'Due', 'Status']],
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
                unique_students = filtered_todos['Student'].unique()

                for i, student in enumerate(unique_students):
                    col = cols[i % 3]
                    student_work = filtered_todos[filtered_todos['Student'] == student]

                    with col:
                        with st.container(border=True):
                            st.write(f"**{student}**")
                            st.table(student_work[['Task', 'Status', 'Due']])
            else:
                st.success("🎉 No assignments found for this time period!")
        else:
            st.success("🎉 No active assignments found!")
