"""Sample Python file for testing code chunking."""
import os
from typing import List


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate a user with username and password.

    Args:
        username: The username
        password: The password

    Returns:
        True if authenticated, False otherwise
    """
    # This is a simple authentication function
    if not username or not password:
        return False

    # Check credentials (dummy implementation)
    return username == "admin" and password == "secret"


class UserManager:
    """Manages user operations."""

    def __init__(self):
        self.users = []

    def add_user(self, username: str, email: str) -> None:
        """Add a new user."""
        user = {"username": username, "email": email}
        self.users.append(user)

    def get_user(self, username: str) -> dict:
        """Get a user by username."""
        for user in self.users:
            if user["username"] == username:
                return user
        return None

    def delete_user(self, username: str) -> bool:
        """Delete a user by username."""
        for i, user in enumerate(self.users):
            if user["username"] == username:
                del self.users[i]
                return True
        return False


def calculate_total(items: List[float]) -> float:
    """Calculate the total of a list of numbers."""
    return sum(items)
