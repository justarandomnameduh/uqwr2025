# VLM Frontend

React frontend for the Vision-Language Model (VLM) chatbot backend.

## Features

- **Text Chat**: Type messages and get AI responses
- **Image Upload**: Upload and send images with your messages
- **Multi-modal**: Support for text + image conversations
- **Real-time**: Instant responses from the VLM backend
- **Modern UI**: Clean, responsive design with Tailwind CSS
- **Audio Ready**: Audio input button prepared for future implementation

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- VLM Backend running on port 5000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables:
```bash
# Create .env file
echo "REACT_APP_API_URL=http://localhost:5000" > .env
echo "PORT=3000" >> .env
```

3. Start the development server:
```bash
npm start
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Backend Connection

Make sure your VLM backend is running on port 5000 before starting the frontend. The frontend will automatically:
- Check backend connectivity
- Display model information
- Show connection status

## Usage

1. **Upload Images**: Use the sidebar to upload images (PNG, JPG, JPEG, GIF, BMP, WEBP)
2. **Select Images**: Click on uploaded images to select them for your message
3. **Type Message**: Enter your text in the input area
4. **Send**: Press Enter or click the send button
5. **Audio**: Audio input button is disabled (coming soon)

## API Configuration

The frontend connects to the backend at `http://localhost:5000` by default. To change this:

1. Set the `REACT_APP_API_URL` environment variable
2. Or modify the API_BASE_URL in `src/services/api.ts`

## Components

- **ChatInterface**: Main chat interface
- **MessageList**: Displays conversation history
- **MessageInput**: Text input and message sending
- **ImageUpload**: Image upload and management
- **StatusBar**: Connection and model status

## Build for Production

```bash
npm run build
```

This builds the app for production to the `build` folder.

## Technologies Used

- React 18 with TypeScript
- Tailwind CSS for styling
- Axios for API calls
- Lucide React for icons
- UUID for unique IDs

## File Structure

```
src/
├── components/          # React components
│   ├── ChatInterface.tsx
│   ├── MessageList.tsx
│   ├── MessageInput.tsx
│   ├── ImageUpload.tsx
│   └── StatusBar.tsx
├── services/           # API services
│   └── api.ts
├── types/             # TypeScript types
│   └── index.ts
├── App.tsx            # Main app component
└── index.tsx          # Entry point
```
