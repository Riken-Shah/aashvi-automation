# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 **IMPORTANT: REFACTORED CODEBASE**

**This repository has been completely refactored with a new architecture.** 

- **✅ New Code**: All files in `config/`, `core/`, `infrastructure/`, `application/` directories
- **📁 Legacy Code**: Original files moved to `legacy_backup/` directory  
- **🚀 Entry Point**: Use `main.py` instead of old scripts

## Project Overview

This is an AI-driven Instagram automation system for a virtual model named "Aashvi". The system generates content, creates images using Stable Diffusion, and automates posting to Instagram.

## Architecture

### Core Components
- **automation.py**: Main content generation and image creation system
  - Connects to Automatic1111 API for Stable Diffusion image generation
  - Manages Google Sheets integration for content tracking
  - Handles OpenAI GPT integration for caption generation
- **utils.py**: Shared utilities for API credentials, messaging, and Google Sheets client
- **post_on_instagram.py**: Instagram posting automation using Selenium
- **approve_process.py**: Content approval notification system
- **story_nudge.py**: Instagram story posting automation
- **any_img_to_aashvi.py**: Face replacement and image processing pipeline
- **run_post_processing.py**: Wrapper script for running the automation

### Key Dependencies
- OpenAI API for caption generation
- Google Sheets API for content management
- Google Drive API for image storage
- Selenium WebDriver for Instagram automation
- Stable Diffusion (Automatic1111) for image generation
- Telegram Bot API for notifications

### File Paths
All scripts reference hardcoded paths to `/Users/rikenshah/Desktop/Fun/insta-model/` for:
- Chrome profile storage
- Image processing directories (raw/, mask/, final/, processed/)
- Configuration files (location.txt, automatic1111_url.txt, is_running.txt)

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Ensure virtual environment is activated before running any scripts
source venv/bin/activate
```

### Running Components
```bash
# Main automation (image generation and captions)
python3 automation.py

# Instagram posting
python3 post_on_instagram.py

# Story notifications
python3 story_nudge.py

# Content approval checks
python3 approve_process.py

# Face processing pipeline
python3 any_img_to_aashvi.py
```

### Scheduled Execution
The `cronjob` file contains cron entries that run various components:
- Every 30 minutes: approve_process.py, automation.py
- Every 60 minutes: any_img_to_aashvi.py
- Every 180 minutes: story_nudge.py
- Every 720 minutes: post_on_instagram.py

## Configuration Requirements

### Environment Variables (.env file required)
- `OPENAI_ORGANIZATION`: OpenAI organization ID
- `OPENAI_API_KEY`: OpenAI API key
- `TELEGRAM_WEBHOOK_URL`: Telegram bot webhook URL
- `GSPREED_KEY`: Google Sheets document key

### Required Files
- `/Users/rikenshah/Desktop/Fun/insta-model/aashvi-model-899f62fffa21.json`: Google service account credentials
- `/Users/rikenshah/Desktop/Fun/insta-model/location.txt`: Current travel location for content generation
- `/Users/rikenshah/Desktop/Fun/insta-model/automatic1111_url.txt`: Stable Diffusion API URL
- `/Users/rikenshah/Desktop/Fun/insta-model/is_running.txt`: Process lock file

## Key Workflows

1. **Content Generation**: automation.py generates prompts and captions based on travel locations
2. **Image Creation**: Stable Diffusion API creates images from prompts
3. **Content Approval**: Manual approval process tracked in Google Sheets
4. **Instagram Posting**: Selenium automation posts approved content
5. **Face Processing**: any_img_to_aashvi.py applies face replacement using masks

## Important Notes

- All image processing requires Automatic1111 Stable Diffusion server to be running
- Google Colab integration for remote GPU usage when local processing unavailable
- Chrome WebDriver profiles maintained for Instagram session persistence
- Telegram bot integration for status notifications and manual story posting