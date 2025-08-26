# RAG Web UI

A modern, production-ready web interface for the RAG Chatbot backend.

## Features

- 🚀 **Streaming Chat**: Real-time streaming responses with Server-Sent Events
- 📄 **Document Ingestion**: Drag-and-drop file uploads and URL ingestion
- 🔍 **Inline Citations**: Clickable source citations with preview drawer
- 🎨 **Dark Mode**: Beautiful dark/light theme support
- 📱 **Responsive**: Works on desktop and mobile devices
- ⚡ **Fast**: Built with Vite and optimized for performance
- 🔧 **Configurable**: Settings panel for API configuration
- 📊 **Debug Panel**: Real-time retrieval metrics and debugging info

## Quick Start

### Prerequisites

- Node.js 18+ 
- pnpm (recommended) or npm
- RAG backend running on `http://localhost:8000`

### Development

1. Install dependencies:
```bash
cd web
pnpm install
```

2. Start the development server:
```bash
pnpm dev
```

The UI will be available at `http://localhost:5173`

### Production Build

1. Build the application:
```bash
pnpm build
```

2. Preview the production build:
```bash
pnpm preview
```

### Docker

Build and run the Docker image:

```bash
# Build the image
docker build -f Dockerfile.web -t rag-web .

# Run the container
docker run -p 5173:80 rag-web
```

## Configuration

### Backend Connection

The UI connects to the RAG backend at `http://localhost:8000` by default. You can change this in the Settings panel.

### CORS Setup

For development, ensure your backend allows CORS from `http://localhost:5173`:

```python
# In your FastAPI app
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## API Integration

The UI integrates with the following backend endpoints:

- `GET /healthz` - Health check
- `GET /readyz` - Readiness check (with API key)
- `POST /query/` - Query endpoint
- `POST /ingest/` - Document ingestion
- `GET /chat/stream` - Streaming chat (SSE)

## Keyboard Shortcuts

- `⌘/Ctrl + Enter` - Send message
- `Esc` - Close dialogs/drawers
- `⌘/Ctrl + K` - Command palette (coming soon)

## Development

### Project Structure

```
web/
├── src/
│   ├── components/     # UI components
│   ├── lib/           # Utilities and API clients
│   ├── state/         # Zustand state management
│   ├── pages/         # Page components
│   └── hooks/         # Custom React hooks
├── public/            # Static assets
├── e2e/              # End-to-end tests
└── tests/            # Unit tests
```

### Testing

```bash
# Unit tests
pnpm test

# E2E tests
pnpm test:e2e

# Test UI
pnpm test:ui
```

### Linting and Formatting

```bash
# Lint
pnpm lint

# Format
pnpm format

# Type check
pnpm type-check
```

## Technologies

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **Zustand** - State management
- **React Router** - Client-side routing
- **Lucide React** - Icons
- **Markdown-it** - Markdown rendering
- **PDF.js** - PDF preview
- **Vitest** - Testing
- **Playwright** - E2E testing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see the main project LICENSE file. 