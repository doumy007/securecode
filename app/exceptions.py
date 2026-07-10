class SecureCodeException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(SecureCodeException):
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message=message, code="NOT_FOUND", status_code=404)


class UnauthorizedException(SecureCodeException):
    def __init__(self, message: str = "No autorizado"):
        super().__init__(message=message, code="UNAUTHORIZED", status_code=401)


class ForbiddenException(SecureCodeException):
    def __init__(self, message: str = "Acceso denegado"):
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class ValidationException(SecureCodeException):
    def __init__(self, message: str = "Error de validación"):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422)


class ConflictException(SecureCodeException):
    def __init__(self, message: str = "Conflicto"):
        super().__init__(message=message, code="CONFLICT", status_code=409)
