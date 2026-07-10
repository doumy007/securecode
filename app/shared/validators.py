import re
from typing import Optional


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple:
    errors = []
    if len(password) < 8:
        errors.append("Mínimo 8 caracteres")
    if not re.search(r"[A-Z]", password):
        errors.append("Debe contener mayúscula")
    if not re.search(r"[a-z]", password):
        errors.append("Debe contener minúscula")
    if not re.search(r"\d", password):
        errors.append("Debe contener número")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Debe contener carácter especial")
    return (len(errors) == 0, errors)


def sanitize_filename(filename: str) -> str:
    filename = re.sub(r"[^\w\-_.]", "_", filename)
    filename = filename.strip("._")
    if not filename:
        filename = "unnamed_file"
    return filename


def validate_url(url: str) -> bool:
    pattern = r"^https?://[\w\-]+(\.[\w\-]+)+[/#?]?.*$"
    return bool(re.match(pattern, url))
