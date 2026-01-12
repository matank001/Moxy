# Contributing to Moxy

Thank you for your interest in contributing to Moxy! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style Guidelines](#code-style-guidelines)
- [Submitting Changes](#submitting-changes)
- [Project Structure](#project-structure)

## Code of Conduct

**Important:** Moxy is designed strictly for ethical security testing and research purposes. It is intended to assist security professionals, developers, and organizations in identifying and remediating vulnerabilities in applications that they own or have explicit permission to test.

By contributing to Moxy, you agree to:
- Use the tool only for authorized security testing
- Respect the privacy and security of others
- Not use Moxy for malicious purposes
- Follow responsible disclosure practices

## Getting Started

Before contributing, please:
1. Read the [README.md](README.md) to understand the project
2. Check existing issues and pull requests to avoid duplicate work
3. Fork the repository and create a new branch for your contribution

## Development Setup

### Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18+** and **npm** (frontend)
- **uv** (Python package manager) - [Installation guide](https://github.com/astral-sh/uv)
- **Git**

### Backend Setup

1. Navigate to the backend directory:
   ```sh
   cd backend
   ```

2. Install dependencies using `uv`:
   ```sh
   uv sync
   ```

3. Run the backend server:
   ```sh
   uv run moxy
   ```

The backend runs on `http://localhost:5000` by default.

### Frontend Setup

1. Navigate to the frontend directory:
   ```sh
   cd frontend
   ```

2. Install dependencies:
   ```sh
   npm install
   ```

3. Start the development server:
   ```sh
   npm run moxy
   ```

The frontend runs on `http://localhost:8080` by default.

### Environment Variables

For AI agent features, create a `.env` file in the `backend` directory:

**OpenAI:**
```env
OPENAI_API_KEY=sk-proj-...
MODEL=gpt-4o-mini
```

**Ollama (Local AI):**
```env
USE_OLLAMA=true
OPENAI_API_KEY=test
OPENAI_BASE_URL=http://localhost:11434/v1/
MODEL=qwen3:8b
```

## How to Contribute

### Reporting Issues

When reporting issues, please include:
- A clear description of the issue
- Steps to reproduce the problem
- Expected vs. actual behavior
- Environment details (OS, Python version, Node version)
- Relevant logs or error messages
- Screenshots if applicable

### Suggesting Features

Feature suggestions are welcome! Please:
- Check if the feature has already been requested
- Provide a clear description of the proposed feature
- Explain the use case and benefits
- Consider implementation complexity

### Pull Requests

1. **Create a branch:**
   ```sh
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes:**
   - Write clean, maintainable code
   - Follow the project's code style
   - Add comments where necessary
   - Update documentation if needed

3. **Test your changes:**
   - Test both backend and frontend if applicable
   - Ensure existing functionality still works
   - Test edge cases

4. **Commit your changes:**
   ```sh
   git commit -m "feat: add new feature"
   # or
   git commit -m "fix: resolve bug in proxy handling"
   ```

5. **Push and create a PR:**
   ```sh
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python (Backend)

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints where appropriate
- Keep functions focused and single-purpose
- Use descriptive variable and function names
- Add docstrings for public functions and classes

Example:
```python
def process_request(request: dict) -> dict:
    """Process an HTTP request and return modified version.
    
    Args:
        request: Dictionary containing request data
        
    Returns:
        Modified request dictionary
    """
    # Implementation
    pass
```

### TypeScript/React (Frontend)

- Follow the existing code style in the project
- Use TypeScript types for all props and state
- Prefer functional components with hooks
- Use meaningful component and variable names
- Keep components small and focused
- Use the existing UI components from `src/components/ui/`

Example:
```typescript
interface RequestListProps {
  requests: Request[];
  onSelect: (request: Request) => void;
}

export function RequestList({ requests, onSelect }: RequestListProps) {
  // Implementation
}
```

### General Guidelines

- **Keep it simple:** Write code that is easy to understand and maintain
- **Comment wisely:** Add comments for complex logic, not obvious code
- **Be consistent:** Follow existing patterns in the codebase
- **Test thoroughly:** Ensure your changes work as expected

## Submitting Changes

### Commit Messages

Use conventional commit format:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add request filtering by status code
fix: resolve memory leak in proxy manager
docs: update API documentation
refactor: simplify request processing logic
```

### Pull Request Process

1. **Update your branch:**
   ```sh
   git checkout main
   git pull upstream main
   git checkout your-branch
   git rebase main
   ```

2. **Write a clear PR description:**
   - What changes were made
   - Why the changes were needed
   - How to test the changes
   - Any breaking changes

3. **Ensure your PR:**
   - Follows the code style guidelines
   - Includes necessary documentation updates
   - Doesn't break existing functionality
   - Has a clear commit history

4. **Respond to feedback:**
   - Be open to suggestions and feedback
   - Make requested changes promptly
   - Ask questions if something is unclear

## Project Structure

```
Moxy/
├── backend/              # Python backend
│   ├── src/
│   │   ├── api/         # API endpoints
│   │   ├── addon.py     # MITMproxy addon
│   │   ├── db.py        # Database operations
│   │   └── ...
│   ├── pyproject.toml   # Python dependencies
│   └── main.py          # Entry point
│
├── frontend/            # React/TypeScript frontend
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── lib/         # Utilities and API client
│   │   ├── pages/       # Page components
│   │   └── ...
│   ├── package.json     # Node dependencies
│   └── vite.config.ts   # Vite configuration
│
└── README.md            # Project documentation
```

### Key Components

- **Backend API:** RESTful API endpoints in `backend/src/api/`
- **Proxy Manager:** MITMproxy integration in `backend/src/proxy_manager.py`
- **MITMproxy Addon:** Request/response capture and interception logic in `backend/src/addon.py`
- **Database:** SQLite databases managed in `backend/src/db.py`
- **Frontend Components:** React components in `frontend/src/components/`
- **UI Library:** shadcn/ui components in `frontend/src/components/ui/`

### MITMproxy Integration

Moxy uses [MITMproxy](https://mitmproxy.org/) as an intercepting HTTP/HTTPS proxy to capture and modify traffic during dynamic application security testing. The proxy runs on **port 8081** by default.

#### MITMproxy Addon (`backend/src/addon.py`)

The `addon.py` file contains the `ProxyRecorder` addon class that integrates Moxy with MITMproxy. This addon is responsible for:

- **Request/Response Capture:** Captures HTTP requests and responses as they flow through the proxy, storing them in the project database
- **Request Interception:** When intercept mode is enabled, the addon can pause requests and wait for user action (forward, drop, or modify)
- **Flow Management:** Manages intercepted flows, allowing users to forward or drop requests individually or in bulk
- **Database Integration:** Synchronizes intercepted flow state with the database, allowing the API and frontend to query and control intercepted requests
- **Project Switching:** Automatically handles project changes and clears intercepted flows when switching between projects

**Key Methods:**
- `request()` - Called when a request is complete; saves the request and handles interception
- `response()` - Called when a response is received; updates the saved request with response data
- `requestheaders()` - Called when request headers are received; checks for forward commands
- `_check_forward_commands()` - Periodically checks the database for forward/drop commands from the API
- `_save_request()` - Saves request data to the project database
- `_update_with_response()` - Updates saved requests with response data

**Important Notes:**
- The addon runs in a separate process from the main Flask API server
- Communication between the addon and API happens through the database (using `db.get_proxy_state()` and `db.set_proxy_state()`)
- The addon uses a background thread for periodic checks since `tick()` doesn't work in `mitmdump` (non-interactive) mode
- When intercept mode is disabled, all queued intercepted flows are automatically forwarded

When working on proxy-related features, familiarize yourself with the MITMproxy addon API and the `addon.py` implementation to understand how requests flow through the system.

## Database Considerations

⚠️ **Important:** The project is in preview/beta stage. There is no guarantee of database migration or backward compatibility between versions. Future versions may break compatibility with old database files.

When making database changes:
- Consider migration strategies
- Document schema changes
- Be aware of potential data loss

## Questions?

If you have questions about contributing:
- Check existing issues and discussions
- Open a new issue with the `question` label
- Review the codebase to understand patterns

Thank you for contributing to Moxy! 🚀
