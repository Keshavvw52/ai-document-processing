# AI Document Processing

An AI-powered document processing app for uploading documents, extracting structured data, reviewing results, and exporting them.

The project has two parts:

- `backend/` - FastAPI backend for upload, OCR, Groq Vision extraction, database storage, and export
- `frontend/` - React/Vite frontend for upload, document library, review, analytics, and UI

## Features

- Upload PDFs and images
- Process invoices, receipts, contracts, forms, ID cards, reports, and more
- OCR text extraction with EasyOCR and Tesseract fallback
- Groq Vision document classification and field extraction
- Document review screen with editable extracted fields
- Table extraction and document summaries
- Export results as JSON, CSV, XLSX, or ZIP
- Analytics dashboard and health status

## Tech Stack

### Backend

- FastAPI
- SQLAlchemy
- SQLite
- EasyOCR
- Tesseract OCR
- Groq Vision
- OpenCV
- PyMuPDF
- Pillow

### Frontend

- React
- Vite
- Tailwind CSS
- Axios
- Recharts
- Lucide React

## Project Structure

```text
ai-document-processing/
  backend/
    src/
      api/routes/        # API endpoints
      core/              # config and database setup
      models/            # SQLAlchemy database models
      schemas/           # Pydantic request/response schemas
      services/          # OCR, Groq, preprocessing, export logic
    requirements.txt
    .env.example

  frontend/
    src/
      pages/             # React pages
      services/          # API client
      utils/             # frontend helpers
    package.json
```

## Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ai-document-processing
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create your local environment file:

```bash
copy .env.example .env
```

Then edit `.env` and add your Groq API key:

```env
GROQ_API_KEY=your-real-groq-api-key
```

Start the backend:

```bash
uvicorn src.main:app --reload
```

Backend runs at:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://127.0.0.1:5173
```

## Environment Variables

Use `backend/.env.example` as the template.

Important values:

```env
GROQ_API_KEY=your-groq-api-key
DATABASE_URL=sqlite+aiosqlite:///./ai_document_processor.db
UPLOAD_DIR=./uploads
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

Do not commit your real `.env` file.

## Main Backend Flow

```text
Upload document
  ↓
Save file and database record
  ↓
Convert PDF to image if needed
  ↓
Preprocess image
  ↓
Run OCR
  ↓
Classify document with Groq Vision
  ↓
Extract structured fields with Groq Vision
  ↓
Save extraction result
  ↓
Review and export from frontend
```

## Important Files

- `backend/src/main.py` - FastAPI app entry point
- `backend/src/api/routes/upload.py` - upload endpoints
- `backend/src/api/routes/routes.py` - documents, extraction, export, stats, health endpoints
- `backend/src/models/models.py` - database tables
- `backend/src/services/document_processor.py` - full processing pipeline
- `backend/src/services/groq_vision.py` - Groq Vision prompts and calls
- `backend/src/services/ocr_engine.py` - OCR logic
- `frontend/src/App.jsx` - frontend routes and layout
- `frontend/src/services/api.js` - frontend API client
- `frontend/src/pages/UploadPage.jsx` - upload UI
- `frontend/src/pages/DocumentsPage.jsx` - document library
- `frontend/src/pages/DocumentReviewPage.jsx` - review and edit extracted data

## Files Not Committed

The following are ignored by `.gitignore`:

```text
backend/.env
backend/venv/
backend/uploads/
backend/*.db
frontend/node_modules/
frontend/dist/
*.log
__pycache__/
```

## Build Frontend

```bash
cd frontend
npm run build
```

This creates:

```text
frontend/dist/
```

`dist/` is generated output and is ignored by Git.

## License

Add your license here.
