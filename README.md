# Subreply

Tiny, but mighty social network. Create an account at https://subreply.com.

Subreply is a lightweight, high-performance social networking platform. It utilizes a hybrid architecture, combining the speed of **Falcon** for API routing and resources with the robustness of **Django** for data modeling and management.

## Features

*   **User Profiles:** Rich profiles with emoji avatars, bios, location, birthdays, and social links.
*   **Social Graph:** Follow/Unfollow mechanism to curate personal feeds.
*   **Posting & Interaction:**
    *   Create posts with text and hashtags.
    *   Threaded replies for structured conversations.
    *   Mention users (`@username`) to notify them.
    *   Save posts to bookmarks.
*   **Messaging:** Private direct messages between users.
*   **Discovery:**
    *   **Feed:** Personalized stream of posts from people you follow.
    *   **Trending:** Popular content across the platform.
    *   **Discover:** Find new people and posts.
    *   **Directory:** Browse all users.
*   **Notifications:** Real-time alerts for mentions, replies, and new followers.

## Tech Stack

*   **Language:** Python 3
*   **Web Framework:** [Falcon](https://falconframework.org/) (Routing, Middleware, Resources)
*   **ORM:** [Django](https://www.djangoproject.com/) (Database Models, Migrations)
*   **Database:** PostgreSQL
*   **Templating:** Jinja2
*   **Server:** Gunicorn
*   **Cryptography:** Fernet (symmetric encryption)

## Installation

### Prerequisites

*   Python 3.8+
*   PostgreSQL (configured to run on port `6432` by default, or modify `project/settings.py`)

### Setup Steps

1.  **Clone the repository:**
    ```shell
    git clone <repository-url>
    cd subreply
    ```

2.  **Prepare the database:**
    ```shell
    createdb subreply
    ```

3.  **Install dependencies:**
    ```shell
    pip3 install -r requirements.txt
    ```

4.  **Configure Environment (`project/local.py`):**
    Create a file named `project/local.py` in the `project/` directory. This file holds your local secrets and configuration.

    You need to generate a valid Fernet key. You can do this via the CLI:
    ```shell
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```
    Copy the output string and paste it into `project/local.py`:

    ```python
    # project/local.py

    # Replace with the key you generated above
    SIGNATURE = 'YOUR_GENERATED_KEY_STRING_HERE'

    DEBUG = True  # Set to False in production

    # SMTP Configuration for emails
    SMTP = {
        "host": "smtp.example.com",
        "port": 587,
        "user": "your_email_user",
        "password": "your_email_password"
    }
    ```

5.  **Run Migrations:**
    Initialize the database schema:
    ```shell
    python3 manage.py migrate
    ```

## Running the Application

Start the application server using Gunicorn:

```shell
gunicorn router:app
```

The application will be accessible at `http://localhost:8000`.

## Project Structure

*   **`router.py`**: The main entry point. Defines the Falcon application and maps URL routes to resources.
*   **`app/`**: Contains the core application logic.
    *   `models.py`: Django models defining the database schema (User, Post, Bond, etc.).
    *   `api.py`: Handles JSON API endpoints.
    *   `resources.py`: Handles HTML page rendering and views.
    *   `forms.py` & `validation.py`: Input handling and validation.
*   **`project/`**: Configuration files (`settings.py`, `local.py`).
*   **`templates/`**: Jinja2 templates for the frontend UI.
*   **`static/`**: Static assets (CSS, JavaScript, images).

## Styleguide

- Easy to read and easy to modify.
- No useless abstractions.
- Speed of 50ms or lower for each request.

## License

- Ideal to use as an internal social network in any organization.
- Easy to install and easy to maintain.
- Cost depends on level of support needed.