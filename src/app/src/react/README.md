# OCI Generative AI Agent - Frontend

A modern React chat interface for Oracle Cloud Infrastructure (OCI) Generative AI Agents, built with Next.js and Material-UI.

## Features

- 🤖 **AI Chat Interface** - Interactive chat with OCI Generative AI Agents
- 🎙️ **Speech Recognition** - Browser-based speech-to-text integration
- 📊 **Rich Content** - Display tables, diagrams, and citations from AI responses
- 📱 **Responsive Design** - Works seamlessly across devices

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- OCI Generative AI Agent backend service running

### Installation

1. Clone the repository:

```bash
git clone https://github.com/ralungei/oci-genai-agent-blackbelt.git
cd oci-genai-agent-blackbelt
```

2. Install dependencies:

```bash
npm install
```

3. Configure environment variables:

```bash
cp .env.example .env.local
```

Edit `.env.local` and set your backend API URL:

```bash
NEXT_PUBLIC_GENAI_API_URL=http://localhost:8000
```

4. Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
src/
├── app/
│   ├── components/
│   │   └── Chat/           # Chat interface components
│   ├── contexts/           # React contexts (Chat, Theme)
│   ├── services/           # API and speech services
│   └── theme/             # Material-UI theme configuration
```

## Configuration

### Backend Integration

The frontend expects a backend API with these endpoints:

- `POST /chat` - Send messages to the AI agent

### Speech Services

The application uses the Web Speech API for browser-based speech recognition.

## Building for Production

```bash
npm run build
npm start
```

## Key Technologies

- **Next.js 15** - React framework
- **Material-UI** - Component library
- **Framer Motion** - Animations
- **React Contexts** - State management
- **Web Speech API** - Speech recognition

## License

This project is open source and available under the [MIT License](LICENSE).
