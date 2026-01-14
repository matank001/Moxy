# Moxy

<div align="center">
  <img src="frontend/public/logo.png" alt="Moxy Logo">
</div>

Moxy (Next-Gen Man in the middle proxy)
Open-source DAST tool for pentesting powered by agentic AI capabilities (Supporting Ollama). Built on top of browser-use, Moxy streamlines dynamic application security testing.

🚀  **INSANELY EASY TO USE**

And it's free, who doesn't like free stuff?

<div align="center">
  <img src="images/main.png" alt="Main Screenshot" width="700">
</div>

> **Preview Alert:**  
> 🚧 Moxy is in active development and currently in **preview/beta**.  
> Expect breaking changes, instability, and missing features.  
> Use at your own risk and follow project updates for latest improvements!


## Quick Start

To run this for now, you need to run the frontend and backend separately.

### Running the Backend

1. **Navigate to the backend directory:**
   ```sh
   cd backend
   ```

2. **Run the backend server:**
   ```sh
   uv sync
   uv run moxy
   ```

---

### Running the Frontend

1. **Navigate to the frontend directory:**
   ```sh
   cd frontend
   ```

2. **Install dependencies:**
   ```sh
   npm install
   ```

3. **Start the frontend development server:**
   ```sh
   npm run moxy
   ```

> **Note:**  
By default, the frontend runs at [http://localhost:8080](http://localhost:8080)  
and the backend runs at [http://localhost:5000](http://localhost:5000)

## Docker Deployment

Moxy can be run using Docker for easier deployment and consistent environments.
In this way you can collaborate and install easily.

### Quick Start with Docker

1. **Build and start the container:**
   ```sh
   docker-compose up -d --build
   ```

2. **Access the application:**
   - **Frontend**: http://localhost:5000
   - **Proxy**: http://localhost:8081

3. **Configure your browser to use the proxy:**
   
   When running in Docker, you need to manually configure your browser to use the proxy:
   
   - **Proxy Host**: `localhost` (or `127.0.0.1`)
   - **Proxy Port**: `8081`
   - **Protocol**: HTTP
   
   > **Note:**  
   > The proxy runs inside the Docker container but is accessible on `localhost:8081` on your host machine.  
   > You can configure proxy settings in your browser's network settings or use browser extensions for proxy management.

4. **View logs:**
   ```sh
   docker-compose logs -f
   ```

5. **Stop the container:**
   ```sh
   docker-compose down
   ```

### Environment Variables

Create a `.env` file in the project root to configure the application (you need to put it inside the `backend/` directory):

> **Note:**  
> The `.env` file is optional. Docker Compose automatically loads it if present (no warning if missing).  
> All project data is persisted in the `projects_data` directory, which is mounted as a volume.

## Agentic Tool

By default, Moxy works without requiring any AI configuration or credentials - even browser-based DAST flows don't use AI unless enabled.

### Enabling Agentic AI

Moxy supports both **OpenAI's API** and **Ollama** (local AI) for agentic features. To enable AI-powered capabilities:

**For local development:** Create an `.env` file in the `backend` directory with the appropriate configuration.

**For Docker:** Create a `.env` file in the project root (same directory as `docker-compose.yml`).

#### Option 1: Using OpenAI API

For cloud-based AI processing with OpenAI, configure your `.env` file as follows:

```env
OPENAI_API_KEY=sk-proj-...             # Your OpenAI API key
MODEL=gpt-4o-mini                       # Optional: defaults to gpt-4o-mini if not specified
```

#### Option 2: Using Ollama (Local AI)

For local AI processing with Ollama, configure your `.env` file as follows:

```env
USE_OLLAMA=true
OPENAI_API_KEY=test                    # Required but value is ignored when using Ollama
OPENAI_BASE_URL=http://localhost:11434/v1/  # Ollama API endpoint
MODEL=qwen3:8b                         # Your preferred Ollama model
```

**Capabilities of the Agent:**
- Query prior captured HTTP requests
- Send/modify/resend new requests
- Operate a real browser (using [browser-use](https://github.com/rluba/browser-use)) for dynamic tests and request creation

The agent uses AI to reason about your application's attack surface, replay or modify traffic, and even drive browser sessions to generate new test scenarios.

> **Warning:**  
> The agentic AI modes are currently experimental and may be unstable.

<div align="center">
  <img src="images/agent.png" alt="Agentic AI Demo" width="600">
</div>



## Proxy

Moxy leverages [MITMproxy](https://mitmproxy.org/) as an intercepting HTTP/HTTPS proxy to capture and modify traffic during dynamic application security testing.

By default, the proxy runs on **port 8081**.
You can configure your browser or system to use `http://localhost:8081` as a proxy to route traffic through MITMproxy and allow Moxy to analyze and interact with requests in real time.

## Database Structure

- `moxy.db` - Main database storing project metadata
- `projects_data/{project_name}.db` - Individual project databases (named after project, sanitized)
  - Each project gets its own SQLite database file
  - When a project is renamed, its database file is automatically renamed
  - When a project is deleted, its database file is removed

> **Warning:**  
> At this stage, **there is no guarantee of database migration or backward compatibility** between versions—future versions may break compatibility with old database files. Use with caution if you plan to upgrade.


## Ethical Use Disclaimer

Moxy is designed **strictly for ethical security testing and research purposes**. It is intended to assist security professionals, developers, and organizations in **identifying and remediating vulnerabilities in applications that they own or have explicit permission to test**.