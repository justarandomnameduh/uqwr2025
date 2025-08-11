# UQ Winter Research Project 2025

This project consists of a Flask backend with HuggingFace VLMs and a React frontend built with TailwindCSS and TypeScript.

## Prerequisites

- Python 3.8+
- Node.js 18+
- npm or yarn

## Installation

```bash
git clone https://github.com/justarandomnameduh/uqwr2025.git
cd uqwr2025
```

### Backend Setup

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Option 1: Use the provided script (Recommended)

From the project root, simply run:
```bash
./run.sh
```

### Option 2: Manual startup

#### Start Backend
```bash
cd backend
python run.py
```

The backend will start on `http://localhost:5000`

#### Start Frontend (in a new terminal)
```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:5173`

## Features

- **Vision Language Model (VLM)**: AI service for image analysis and text generation
- **Transcription Service**: Audio-to-text conversion using Whisper
- **Chat Interface**: Interactive chat with AI models
- **File Upload**: Support for image and audio files
- **Real-time Streaming**: Streaming responses from AI models

## License

This project is part of UQ Winter Research 2025.

## The project is still a work in progress.
