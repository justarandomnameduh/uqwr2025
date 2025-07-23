# VLM Frontend

A modern React frontend for the Vision-Language Model (VLM) chatbot backend, built with Vite, TypeScript, and TailwindCSS.

## Features

- **💬 Text Chat**: Type messages and get AI responses
- **🖼️ Image Upload**: Upload and send images with your messages (drag & drop, multi-select)
- **🎤 Audio Transcription**: Upload audio files for automatic transcription
- **🔄 Multi-modal**: Support for text + image conversations
- **⚡ Real-time**: Instant responses from the VLM backend
- **🎨 Modern UI**: Beautiful, responsive design with TailwindCSS
- **📱 Mobile-friendly**: Responsive design that works on all devices
- **🔌 Connection Monitoring**: Real-time backend connectivity status

## Tech Stack

- **React 19** with TypeScript
- **Vite** for fast development and building
- **TailwindCSS** for modern styling
- **Axios** for API calls
- **Lucide React** for icons
- **Marked** for markdown rendering
- **UUID** for unique IDs

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- VLM Backend running on port 5000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env if your backend is running on a different port
echo "VITE_API_URL=http://localhost:5000" > .env
```

3. Start the development server:
```bash
npm run dev
```

4. Open your browser and navigate to the URL shown in the terminal (usually `http://localhost:5173`)

### Backend Connection

Make sure your VLM backend is running on port 5000 before starting the frontend. The frontend will automatically:
- Check backend connectivity every 30 seconds
- Display model information and status
- Show connection errors if the backend is unavailable

## Usage

### Basic Chat
1. Type your message in the input area at the bottom
2. Press Enter or click the send button
3. The AI will respond with generated text

### Image Conversations
1. **Upload Images**: 
   - Use the sidebar on the right to upload images
   - Drag and drop files or click "Select Files"
   - Supported formats: PNG, JPG, JPEG, GIF, BMP, WEBP
   - Maximum file size: 16MB per file

2. **Select Images for Conversation**:
   - Click on uploaded images to select them (blue border indicates selection)
   - Selected images will be included with your next message
   - You can select multiple images at once

3. **Send Multi-modal Messages**:
   - Type your text and/or select images
   - Send the message - images will be analyzed by the VLM

### Audio Transcription
1. Click the microphone button in the message input area
2. Select an audio file (MP3, WAV, FLAC, OGG, M4A, AAC, or video files)
3. Wait for transcription to complete
4. The transcribed text will be automatically added to your message
5. Edit or send the message as normal

### Managing Content
- **Clear Chat**: Remove all conversation history
- **Clear Images**: Delete all uploaded images
- **Remove Individual Images**: Click the X button on any uploaded image

## API Configuration

The frontend connects to the backend at `http://localhost:5000` by default. To change this:

1. Set the `VITE_API_URL` environment variable in your `.env` file
2. Restart the development server

## Component Architecture

```
src/
├── components/          # React components
│   ├── ChatInterface.tsx    # Main chat interface with state management
│   ├── MessageList.tsx      # Message display with markdown support
│   ├── MessageInput.tsx     # Text input with image preview
│   ├── ImageUpload.tsx      # Image upload with drag & drop
│   ├── AudioUpload.tsx      # Audio file upload and transcription
│   └── StatusBar.tsx        # Connection and model status
├── services/           # API services
│   └── api.ts              # Backend API integration
├── types/             # TypeScript type definitions
│   └── index.ts
├── utils/             # Utility functions
│   └── markdown.tsx        # Markdown rendering component
├── App.tsx            # Main app component
└── main.tsx           # Application entry point
```

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Building for Production

```bash
npm run build
```

This builds the app for production to the `dist` folder. The build is optimized and ready for deployment.

## Features in Detail

### Connection Management
- Automatic backend health checks every 30 seconds
- Visual connection status indicator
- Error handling with user-friendly messages
- Graceful degradation when backend is unavailable

### Image Handling
- Client-side image preview before upload
- Progress indicators during upload
- Error handling for failed uploads
- Memory management (automatic cleanup of object URLs)
- Drag & drop interface with visual feedback

### Audio Processing
- Support for multiple audio and video formats
- Real-time transcription progress
- Error handling for transcription failures
- Automatic text insertion into message input

### Message Display
- Markdown rendering for AI responses
- Syntax highlighting for code blocks
- Image display within messages
- Timestamp display
- Typing indicator during AI generation
- Automatic scroll to latest messages

### Responsive Design
- Mobile-first approach
- Flexible sidebar that adapts to screen size
- Touch-friendly interface elements
- Optimized for both desktop and mobile use

## Troubleshooting

### Backend Connection Issues
- Ensure the backend server is running on the correct port
- Check the `VITE_API_URL` environment variable
- Verify CORS settings on the backend
- Check browser console for network errors

### Image Upload Problems
- Verify file formats are supported
- Check file size limits (16MB max)
- Ensure backend upload endpoint is working
- Check available disk space

### Audio Transcription Issues
- Verify audio file format is supported
- Check file size (100MB max for audio)
- Ensure transcription service is running on backend
- Check microphone permissions if using live recording (future feature)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the VLM Chat system and follows the same licensing terms.
