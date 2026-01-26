# Nexus Agent

Nexus Agent is a private, multimodal intelligent control center powered by a Local LLM (or API) as its core computing unit.

## Phase 1: MVP

This version implements the core "Think -> Act -> Reply" loop using LangGraph and FastAPI.

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key (or compatible)

### Setup & Run

1. **Set API Key**:
   Create a `.env` file in the root directory:
   ```bash
   OPENAI_API_KEY=sk-your-api-key-here
   ```

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Test the API**:
   You can send a POST request to the `/chat` endpoint:

   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What time is it?"}'
   ```

   Or:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Calculate 123 * 456"}'
   ```

### Project Structure

- `app/core/`: Application core (Agent State, LangGraph definition)
- `app/tools/`: Tool registry and tool definitions
- `app/main.py`: FastAPI entry point

