# Football Pro Stats

A full-stack application for tracking professional football statistics.

## Tech Stack

- **Frontend:** Next.js 16 + React 19 + TypeScript + Tailwind CSS
- **Backend:** Python FastAPI

## Project Structure

```
football-pro-stats/
├── frontend/          # Next.js app
│   ├── src/app/       # App router pages
│   ├── package.json
│   └── ...
├── backend/           # Python FastAPI server
│   ├── main.py        # API entry point
│   └── requirements.txt
└── README.md
```

## Getting Started

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload  # http://localhost:8000
```

## API Endpoints

| Method | Endpoint        | Description       |
|--------|-----------------|-------------------|
| GET    | `/`             | API root          |
| GET    | `/api/health`   | Health check      |
