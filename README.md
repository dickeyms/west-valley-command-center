# West Valley Command Center

A secure Streamlit application for monitoring student assignments from Canvas LMS. Built for Teacher Aides to track to-do lists for multiple students in real-time.

## Features

- **Password Protected**: Secure access control before displaying any data
- **Multi-Student Monitoring**: Track 11 students simultaneously
- **Flexible Timeframes**: Filter by This Week, Next Week, 3 Weeks, or All Tasks 
- **Master List View**: See all tasks from all students in one table
- **Student Breakdown**: Individual cards showing each student's assignments
- **Real-time Sync**: Direct Canvas API integration for up-to-date information

## Deployment on Streamlit Community Cloud

### Step 1: Push to GitHub

1. **Initialize Git Repository** (if not already done):
   ```bash
   cd /Users/mdickey/Documents/Scripts
   git init
   git add .
   git commit -m "Initial commit: West Valley Command Center"
   ```

2. **Create GitHub Repository**:
   - Go to [github.com](https://github.com) and create a new repository
   - Name it something like `west-valley-command-center`
   - Do NOT initialize with README (you already have one)

3. **Push to GitHub**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/west-valley-command-center.git
   git branch -M main
   git push -u origin main
   ```

### Step 2: Deploy on Streamlit Community Cloud

1. **Go to Streamlit Community Cloud**:
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Deploy New App**:
   - Click "New app"
   - Select your repository: `YOUR_USERNAME/west-valley-command-center`
   - Set Main file path: `class_monitor.py`
   - Click "Deploy"

3. **Add Secrets**:
   - In the Streamlit Cloud dashboard, click on your app
   - Go to "Settings" → "Secrets"
   - Copy the contents from your local `.streamlit/secrets.toml` file
   - Paste into the secrets editor
   - Click "Save"

### Step 3: Access Your App

Your app will be live at: `https://YOUR_USERNAME-west-valley-command-center.streamlit.app`

Share this URL with your Teacher Aides!

## Local Development

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

1. Copy the secrets template:
   ```bash
   cp .streamlit/secrets.toml.template .streamlit/secrets.toml
   ```

2. Edit `.streamlit/secrets.toml` and add:
   - Your app password
   - Canvas API tokens for each student

### Running Locally

```bash
streamlit run class_monitor.py
```

## Security

- **No Hardcoded Secrets**: All tokens stored in `secrets.toml` (gitignored)
- **Password Authentication**: App requires password before displaying data
- **Secure Deployment**: Secrets managed through Streamlit Cloud's encrypted secrets management

## Students Monitored

- DavidS
- Jonathan
- DavidM
- Anirudh
- Alex
- Jesus
- Olivia
- Angel
- Tava
- Heidy
- Melody

## Canvas API

- **Base URL**: `https://wvm.instructure.com`
- **Endpoint**: `/api/v1/planner/items`
- **Authentication**: Bearer token (per student)

## Tech Stack

- **Frontend**: Streamlit
- **Data Processing**: Pandas
- **API Calls**: Requests
- **Hosting**: Streamlit Community Cloud

## Troubleshooting

### App Won't Deploy
- Check that `requirements.txt` is in the repository root
- Verify `class_monitor.py` path is correct
- Ensure secrets are properly formatted in Streamlit Cloud

### Password Issues
- Secrets must be added in Streamlit Cloud dashboard
- Check for typos in the secrets format
- Verify the password field is exactly: `[passwords]` then `auth = "your_password"`

### Token Errors
- Generate new tokens in Canvas: Account → Settings → New Access Token
- Update tokens in Streamlit Cloud secrets (not in code!)
- Ensure token names match student names exactly

## License

Private educational tool. Not for public distribution.

## Support

For issues or questions, contact the system administrator.
