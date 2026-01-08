# Release Notes - v1.0.0

**Auto-Blogging System for Thai Cosmetic Products**

## Overview
This is the initial release of the fully automated blogging system designed to generate SEO-friendly, compliant articles for Thai cosmetic products. It leverages Google's Gemini 3 AI to create "soft-sell" content that educates users while promoting products.

## Key Features
- **AI-Powered Generation**: Creates engaging articles using "Soft Sell" prompt engineering (80% education, 20% promotion).
- **Compliance First**: Built-in support for filtering content against Thai FDA cosmetic regulations (mock rules active, adaptable to real PDF data).
- **Automated Publishing**: Deploys content directly to WordPress sites via REST API.
- **Robust CLI**: Supports `daily` mode for automation and `dry_run` for verification.

## Installation & Usage
See `setup_guide.md` for detailed instructions.

```bash
# Quick Start
pip install -r requirements.txt
python main.py --dry_run
```

## Known Issues
- Real-time Gemini API compliance processing requires a stable model ID configuration (currently using mock rules).
