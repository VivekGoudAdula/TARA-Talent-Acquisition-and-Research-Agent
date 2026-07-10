# Tara Backend

This is the backend component of the Tara application.

## Prerequisites

- Python 3.11+
- Virtual environment (`.venv`)

## Getting Started

1. Copy `.env.example` to `.env` (or use the hard-linked `.env` at the root).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server from the **backend** directory (required — `app` is not on the Python path from the repo root):

   ```bash
   cd backend
   ..\.venv\Scripts\Activate.ps1

   uvicorn app.main:app --reload
   ```

   Or from the repo root:

   ```bash
   cd backend && uvicorn app.main:app --reload
   ```

   Alternative:

   ```bash
   cd backend
   python app/main.py
   ```