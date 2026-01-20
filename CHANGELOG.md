# Changelog

All notable changes to this project will be documented in this file.

## [2.2.0] - 2026-01-20

### Added
- **Product Data CSV**: Support for `product_data.csv` as a primary product source. The system now randomly selects products from CSV or falls back to text files.
- **Auto-Scheduling**: Posts are now scheduled with a random offset (10-120 minutes) instead of immediate publishing, using WordPress 'future' status.
- **Enhanced Maintenance**: Integrated advanced SEO auditing and Fact-Checking logic (from 'Auto-Blogger-WP') into `maintenance_agent.py`.
- **Publisher Upgrade**: Updated `publisher.py` to support `date` parameter for scheduling.

## [1.0.0] - 2024-01-08

### Added
- **Product Loader**: Module to read and parse product information from text files (`product_loader.py`).
- **Content Generator**: AI-powered content generation using Google Gemini 3, featuring "Soft Sell" strategy (`generator.py`).
- **Compliance Engine**: Automated compliance checks against Thai Cosmetic Act rules (currently using mock rules in `compliance_rules.json`).
- **Publisher**: WordPress REST API integration for automated posting (`publisher.py`).
- **Orchestration**: CLI tool (`main.py`) to manage daily workflows and dry runs.
- **Documentation**: `setup_guide.md` for installation and task scheduling.
- **Testing**: Unit test suite (`tests/test_core.py`) with mocked external dependencies.

### Configuration
- Environment variable support via `.env` for API keys and WordPress credentials.
- Configurable AI model selection (`GEMINI_MODEL_NAME`).
