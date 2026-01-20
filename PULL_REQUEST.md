# Release v2.2.0: CSV Support, Auto-Scheduling, & Enhanced Maintenance

## 🔍 Description
This release introduces significant enhancements to the Auto-Blogging DPLUS system, focusing on automation flexibility, content diversity, and post quality.

## ✨ Key Features
- **CSV Product Data**: `product_data.csv` is now the primary source for products, supporting random selection (Refs `product_loader.py`, `main.py`).
- **Smart Auto-Scheduling**: Posts are now scheduled with a random 10-120 minute offset using WordPress futures (Refs `publisher.py`, `main.py`).
- **Enhanced Maintenance**: Integrated advanced audit logic (Fact Check, Internal Linking, Soft Sell) from the 'Auto-Blogger-WP' repository (Refs `maintenance_agent.py`).

## 🧪 Testing
- Added `tests/test_new_features.py`.
- Verified CSV loading with 100% success.
- Verified Scheduling parameter transmission to WordPress API.
- All existing tests passed.

## 📦 Artifacts
- `CHANGELOG.md` updated.
- `RELEASE_NOTES.md` created.
