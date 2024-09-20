# Newsletter Subscription Service

This is a FastAPI-based newsletter subscription service integrated with Resend.com for email management.

## Setup and Installation

1. Clone the repository:
   ```
   git clone <repository_url>
   cd <repository_name>
   ```

2. Install the required dependencies:
   ```
   pip install poetry
   poetry install
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add the following variables:
   ```
   RESEND_API_KEY=your_resend_api_key_here
   RESEND_AUDIENCE_ID=your_resend_audience_id_here
   ```

4. Customize email templates:
   Edit the `welcome_email_template.html` file to customize the welcome email sent to new subscribers.

## Running the Application

1. Start the FastAPI server:
   ```
   poetry run python main.py
   ```

2. Access the application:
   Open a web browser and navigate to `http://localhost:8000` to view the subscription form and analytics dashboard.

## Features

- Newsletter subscription and unsubscription
- Welcome email sent to new subscribers
- Rate limiting to prevent abuse
- Analytics dashboard
- Customizable email templates

## API Endpoints

- `POST /subscribe`: Subscribe a new user
- `POST /unsubscribe`: Unsubscribe a user
- `GET /analytics`: Get subscription analytics
- `GET /preferences/{email}`: Get subscriber preferences

## Development

To run the application in development mode with auto-reloading:

```
uvicorn main:app --reload
```

## Deployment

This application is designed to be deployed on Replit. Follow these steps to deploy:

1. Create a new Repl on Replit
2. Upload the project files to the Repl
3. Set up the environment variables in the Repl's Secrets tab
4. Click on the "Run" button to start the application

The application will be accessible via the URL provided by Replit.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
