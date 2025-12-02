# Frontend - Docs Journey Builder

Next.js frontend for the Docs Journey Builder application.

## Setup

```bash
cd frontend
bun install
```

## Development

```bash
# Start dev server (runs on http://localhost:3000)
bun run dev
```

Make sure the backend API is running on `http://localhost:8000`.

## Features

- **Chat Input**: Enter your goal to generate a journey
- **Vertical Timeline**: Visual step-by-step journey display
- **Step Details**: Click any step to see detailed information
- **Documentation Links**: Direct links to relevant docs

## Project Structure

```
frontend/
  app/
    page.tsx          # Main page
    layout.tsx        # Root layout
    globals.css       # Global styles
  components/
    JourneyChat.tsx   # Chat input component
    JourneyTimeline.tsx # Timeline display
    StepDetail.tsx    # Step detail panel
```

## API Integration

The frontend connects to the backend API via Next.js rewrites (configured in `next.config.js`).

API endpoint: `POST /api/journey/generate`
