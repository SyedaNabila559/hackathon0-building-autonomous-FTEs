"""
LinkedIn OAuth 2.0 Token Retrieval Script
==========================================

This script starts a local HTTP server to handle the OAuth callback,
opens your browser for LinkedIn authentication, and exchanges the
authorization code for an access token.

Usage:
    python get_linkedin_token.py

Requirements:
    - LINKEDIN_CLIENT_ID in .env
    - LINKEDIN_CLIENT_SECRET in .env
    - Redirect URI set to http://localhost:8000 in LinkedIn Developer Portal
"""

import os
import sys
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# LinkedIn OAuth Configuration
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000"

# LinkedIn OAuth endpoints
AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

# Scopes for LinkedIn API access
# Common scopes: openid, profile, email, w_member_social (for posting)
SCOPES = ["openid", "profile", "email", "w_member_social"]


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        # Parse the URL and query parameters
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if "code" in query_params:
            # Got the authorization code
            auth_code = query_params["code"][0]
            self.server.auth_code = auth_code

            # Send success response to browser
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            success_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>LinkedIn OAuth Success</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: linear-gradient(135deg, #0077B5 0%, #00A0DC 100%);
                        color: white;
                    }
                    .container {
                        text-align: center;
                        padding: 40px;
                        background: rgba(255,255,255,0.1);
                        border-radius: 16px;
                        backdrop-filter: blur(10px);
                    }
                    h1 { margin-bottom: 10px; }
                    p { opacity: 0.9; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    <p>Your access token will be displayed there.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())

        elif "error" in query_params:
            # OAuth error
            error = query_params.get("error", ["unknown"])[0]
            error_description = query_params.get("error_description", ["No description"])[0]
            self.server.auth_code = None
            self.server.error = f"{error}: {error_description}"

            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>OAuth Error</title></head>
            <body>
                <h1>Authentication Failed</h1>
                <p>Error: {error}</p>
                <p>{error_description}</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())

        else:
            # Unknown request
            self.send_response(404)
            self.end_headers()


def exchange_code_for_token(auth_code: str) -> dict:
    """
    Exchange authorization code for access token.

    Args:
        auth_code: The authorization code from OAuth callback

    Returns:
        dict with token response or error
    """
    import urllib.request
    import json

    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    request = urllib.request.Request(TOKEN_URL, data=data, headers=headers)

    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return {"error": f"HTTP {e.code}", "error_description": error_body}
    except Exception as e:
        return {"error": "request_failed", "error_description": str(e)}


def main():
    # Validate environment variables
    if not CLIENT_ID:
        print("Error: LINKEDIN_CLIENT_ID not found in .env")
        sys.exit(1)

    if not CLIENT_SECRET:
        print("Error: LINKEDIN_CLIENT_SECRET not found in .env")
        sys.exit(1)

    print("=" * 60)
    print("LinkedIn OAuth 2.0 Token Retrieval")
    print("=" * 60)
    print(f"\nClient ID: {CLIENT_ID[:10]}...")
    print(f"Redirect URI: {REDIRECT_URI}")
    print(f"Scopes: {', '.join(SCOPES)}")

    # Build authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": "linkedin_oauth_state_12345",  # In production, use a random value
    }

    auth_url = f"{AUTHORIZATION_URL}?{urllib.parse.urlencode(auth_params)}"

    print("\n" + "-" * 60)
    print("Starting local server on http://localhost:8000")
    print("-" * 60)

    # Start the HTTP server
    server = HTTPServer(("localhost", 8000), OAuthCallbackHandler)
    server.auth_code = None
    server.error = None

    # Open browser for authentication
    print("\nOpening browser for LinkedIn authentication...")
    print("If browser doesn't open, visit this URL manually:\n")
    print(auth_url)
    print()

    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for authentication callback...")
    server.handle_request()  # Handle single request

    if server.error:
        print(f"\nError: {server.error}")
        sys.exit(1)

    if not server.auth_code:
        print("\nNo authorization code received.")
        sys.exit(1)

    print("\nAuthorization code received!")
    print("Exchanging code for access token...")

    # Exchange code for token
    token_response = exchange_code_for_token(server.auth_code)

    if "error" in token_response:
        print(f"\nError getting token: {token_response['error']}")
        print(f"Description: {token_response.get('error_description', 'N/A')}")
        sys.exit(1)

    # Success!
    print("\n" + "=" * 60)
    print("SUCCESS! Your LinkedIn Access Token:")
    print("=" * 60)
    print(f"\n{token_response.get('access_token')}\n")
    print("=" * 60)

    print(f"\nToken Type: {token_response.get('token_type', 'N/A')}")
    print(f"Expires In: {token_response.get('expires_in', 'N/A')} seconds")

    if token_response.get("refresh_token"):
        print(f"\nRefresh Token: {token_response['refresh_token']}")

    print("\n" + "-" * 60)
    print("Add this to your .env file:")
    print("-" * 60)
    print(f"\nLINKEDIN_ACCESS_TOKEN={token_response.get('access_token')}")

    if token_response.get("refresh_token"):
        print(f"LINKEDIN_REFRESH_TOKEN={token_response.get('refresh_token')}")

    print()


if __name__ == "__main__":
    main()
