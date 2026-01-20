# Auto-Blogging DPLUS v2.2.0 Release Notes

We are excited to announce version 2.2.0 of Auto-Blogging DPLUS! This release focuses on automation flexibility and content quality.

## 🚀 Key Features

### 1. CSV Product Data Support
You can now manage your product list in a simple `product_data.csv` file.
- **Priority Loading**: The system prioritizes products in the CSV over individual text files.
- **Random Selection**: Products are randomly selected from the CSV to ensure variety.
- **Compatibility**: The old text-file method still works as a fallback.

### 2. Smart Auto-Scheduling
Avoid "bot-like" behavior with random scheduling.
- **Random Offset**: Posts are scheduled 10 to 120 minutes in the future.
- **WordPress Integration**: Uses native WordPress scheduling (`future` status).

### 3. Enhanced Maintenance Agent
Your old posts get smarter updates.
- **Fact Checking**: The maintenance agent now explicitly checks for outdated info and updates it for 2026.
- **Internal Linking**: Automatically identifies opportunities for internal links.
- **SEO & Tone**: Improved prompts for "click-bait" professional titles and "soft sell" tone.

## 🛠 Usage
1.  Populate `product_data.csv` with your products (Name, Description, Keywords).
2.  Run `main.py` as usual.
    ```bash
    python main.py --mode daily
    ```

## 🧪 Testing
New unit tests (`tests/test_new_features.py`) cover CSV loading and Scheduling. Run them with:
```bash
python tests/test_new_features.py
```
