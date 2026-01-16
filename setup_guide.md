- [x] v2.0: Multi-Agent Scientific Research & Maintenance enabled.

## 1. Installation

1.  **Install Python**: Ensure Python 3.10+ is installed.
2.  **Install Dependencies**:
    ```powershell
    pip install -r requirements.txt
    ```
    (Or manually: `pip install google-generativeai requests pydantic python-dotenv`)
3.  **Configure Environment**:
    - Create a `.env` file in the project folder.
    - Add your keys:
        ```text
        GEMINI_API_KEY=AIzaSy...
        WP_URL=https://your-site.com
        WP_USER=your_username
        WP_APP_PASSWORD=your_app_password
        GEMINI_MODEL_NAME=gemini-2.5-flash
        ```

## 2. Compliance Setup
1.  Ensure `Products Data/` contains your product `.txt` files.
2.  Ensure `compliance_rules.json` is generated (run `python process_compliance.py` once).

## 3. Manual Usage
- **Dry Run (Test without publishing)**:
    ```powershell
    python main.py --dry_run
    ```
- **Publish Daily Topic**:
    ```powershell
    python main.py --mode daily
    ```

## 4. Multi-Agent Workflow (v2.0)
The system now uses 4 specialized agents:
- **Researcher Agent**: Gathers scientific citations (PubMed/Science journals) for your ingredients.
- **Generator Agent**: Writes the "Soft Sell" article using research data.
- **Reviewer Agent**: Audits every post for Thai FDA compliance and tone before publishing.
- **Maintenance Agent**: Automatically reviews and updates old posts daily to fix errors or add new scientific findings.

## 4. Automation (GitHub Actions "The Bot")
The "Bot" is actually a **GitHub Action** workflow that runs on GitHub's servers automatically. It is defined in `.github/workflows/auto_blog.yml`.

### How to Activate the Bot:
You do NOT need to run anything on your computer. You just need to set up the **Secrets** on GitHub so the bot can access your WordPress and Google Cloud.

1.  Go to your GitHub Repository page.
2.  Click **Settings** tab.
3.  On the left menu, click **Secrets and variables** -> **Actions**.
4.  Click **New repository secret** (green button).
5.  Add these EXACT secret names and values:

| Secret Name | Value |
| :--- | :--- |
| `WP_URL` | Your WordPress URL (e.g., `https://dplusskin.co.th`) |
| `WP_USER` | Your WordPress Username |
| `WP_APP_PASSWORD` | Your WordPress Application Password (NOT your login password) |
| `GOOGLE_CLOUD_PROJECT` | `auto-blogging-dplus` |
| `GCP_SERVICE_ACCOUNT_KEY` | Paste the ENTIRE content of your JSON key file here |

### Schedule
- **Daily Post**: Runs every day at **10:00 AM Thailand Time** (03:00 UTC).
- **Maintenance**: Runs every Sunday at **10:00 AM Thailand Time**.

### How to Check if it's Running
1.  Go to the **Actions** tab in your GitHub repository.
2.  You will see "Auto-Blogging Daily" listed on the left.
3.  Green checkmark = Success. Red X = Error (click to see logs).
