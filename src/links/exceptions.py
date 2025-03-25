from fastapi import HTTPException, status


class APIError(HTTPException):
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail)
        self.headers = headers


class LinkNotFoundError(APIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )


class NonUniqueAliasError(APIError):
    def __init__(self, alias: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alias '{alias}' already exists"
        )


class NonUniqueShortCodeError(APIError):
    def __init__(self, code: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Short code '{code}' already exists"
        )


class PermissionDenied(APIError):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You cannot manage this link."
        )


class UrlAlreadyExists(APIError):
    def __init__(self, url: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"URL '{url}' already has been shorten"
        )


class AliasLengthError(APIError):
    def __init__(self, alias: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alias length must be between 4 and 16 symbols"
        )
