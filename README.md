<div align="center">

# Flet-Chat

[![CI](https://github.com/HardMax71/Flet-Chat/workflows/CI/badge.svg)](https://github.com/HardMax71/Flet-Chat/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/HardMax71/Flet-Chat/ci.yml?label=tests&branch=main)](https://github.com/HardMax71/Flet-Chat/actions/workflows/ci.yml)
[![Lint](https://img.shields.io/github/actions/workflow/status/HardMax71/Flet-Chat/ci.yml?label=lint&branch=main)](https://github.com/HardMax71/Flet-Chat/actions/workflows/ci.yml)
[![Type Check](https://img.shields.io/github/actions/workflow/status/HardMax71/Flet-Chat/ci.yml?label=mypy&branch=main)](https://github.com/HardMax71/Flet-Chat/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/HardMax71/Flet-Chat/branch/main/graph/badge.svg)](https://codecov.io/gh/HardMax71/Flet-Chat)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/d692dbdd8ec541799947f81fe3a41b65)](https://app.codacy.com/gh/HardMax71/Flet-Chat/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)

[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

## 🚀 Features

- Real-time messaging
- User authentication and authorization
- Persistent login sessions (secure token storage)
- Client-side form validation with real-time feedback
- Strong password requirements and validation
- Group chat functionality
- Message history and search
- Responsive UI design
- Docker support for easy deployment

## 🛠️ Tech Stack

- **Frontend**: [Flet](https://flet.dev/) - A framework for building interactive multi-platform applications in Python
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) - A modern, fast (high-performance) web framework for building APIs with Python
- **Database**: [PostgreSQL](https://www.postgresql.org/) - A powerful, open-source object-relational database system
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/) - The Python SQL toolkit and Object-Relational Mapping (ORM) library
- **Data Validation**: [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings management using Python type annotations
- **Secure Storage**: [Keyring](https://github.com/jaraco/keyring) - Cross-platform token and credential storage
- **Containerization**: [Docker](https://www.docker.com/) and Docker Compose

## 🚀 Getting Started

Follow these steps to get Flet-Chat up and running on your local machine:

<details>
<summary>Click to expand step-by-step instructions</summary>

### Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher

### Environment Configuration

1. **Set up Environment Variables**

   Copy the example environment file and configure with your values:

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file and replace the placeholder values with secure configurations:

   ```bash
   # Generate strong secrets using Python
   python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
   python3 -c "import secrets; print('REFRESH_SECRET_KEY=' + secrets.token_urlsafe(32))"
   python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(16))"
   ```

   **⚠️ Security Note**: Never commit the `.env` file to version control. Use strong, unique passwords and secret keys in production.

### Starting the Application

1. **Start the Backend Services**

   Navigate to the project root directory and run:

    ```bash
    docker-compose up -d
    ```
   
    This command will start the PostgreSQL database, Redis, and the FastAPI backend service.

2. **Start the Frontend Flet App**

    a. Create a virtual environment:

    ```bash
    python -m venv venv
    ```
   
    b. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```bash
     source venv/bin/activate
     ```

    c. Install the required packages:
    
    ```bash
    pip install -r requirements.txt
    ```

    d. Run the Flet application:

    ```bash
    python main.py --web  # also possible: flet run
    ```

This will launch the Flet application, and you should see a window open with the chat interface.

3. **Accessing the Application**

- The Flet frontend application will be running as a desktop app.
- The FastAPI backend will be accessible at `http://localhost:8000`.

</details>

## 📚 Documentation

For comprehensive documentation on Flet-Chat, please refer to our [GitHub Wiki](https://github.com/HardMax71/Flet-Chat/wiki). The wiki provides detailed information on installation, usage, architecture, and more.

For API-specific documentation, once the application is running, you can access:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

For any questions or feedback, please open an issue on the GitHub repository.

Happy chatting! 🎉