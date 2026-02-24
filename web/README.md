# Nexus Agent OS - Web Frontend

This is the modern web frontend layer for Nexus Agent OS, built with [Next.js](https://nextjs.org) (App Router), React, TypeScript, and Tailwind CSS. It connects to the FastAPI backend running in the parent directory.

## Getting Started

1. Ensure you have Node.js installed (v18+ recommended).
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Architecture

This Next.js app is the primary user interface, gradually deprecating Streamlit. It fetches data from the backend (typically on `http://127.0.0.1:8000`).

- **App Router:** Routing and API requests.
- **Tailwind CSS:** Utility-first styling.
