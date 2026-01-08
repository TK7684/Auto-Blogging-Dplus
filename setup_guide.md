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

## 4. Automation (Windows Task Scheduler)
To run the script every day at 10:00 AM:

1.  Open **Task Scheduler** (Search in Start Menu).
2.  Click **Create Basic Task**.
3.  **Name**: `AutoBlogging_Daily`.
4.  **Trigger**: Daily -> Start: 10:00:00 AM -> Recur every 1 days.
5.  **Action**: Start a program.
6.  **Program/script**: `python` (or full path to python.exe e.g., `C:\Python39\python.exe`).
7.  **Add arguments**: `main.py --mode daily`
8.  **Start in**: `C:\Users\ttapk\PycharmProjects\pythonProject\Auto-Blogging-DPLUS` (The project folder is CRITICAL).
9.  Click **Finish**.

> **Note**: Ensure your computer is ON at 10 AM.
