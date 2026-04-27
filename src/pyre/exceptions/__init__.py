"""pyre exceptions — all exception classes live here."""


class GeneralException(Exception):
    """
    Custom exception class for handling errors related to exposures.
    """

    def __init__(self, message: str, identifier: str | None = None):
        """
        Initialize the exception with an error message and optional exposure ID.

        Args:
            message (str): The error message describing the exception.
            id (str, optional): The ID of the exposure related to the error.
        """
        self.message = message
        self.identifier = identifier
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """
        Format the exception message to include the ID if provided.

        Returns:
            str: The formatted exception message.
        """
        if self.identifier:
            return f"Exception: {self.message} (ID: {self.identifier})"
        return f"Exception: {self.message}"


class ExposureException(GeneralException):
    def __init__(self, message: str, exposure_id: str | None):
        super().__init__(message, exposure_id)


class ClaimsException(GeneralException):
    def __init__(self, message: str, claim_id: str | None):
        super().__init__(message, claim_id)
        self.claim_id = claim_id


class ContractException(GeneralException):
    def __init__(self, message: str, contract_id: str | None):
        super().__init__(message, contract_id)


__all__ = [
    "GeneralException",
    "ExposureException",
    "ClaimsException",
    "ContractException",
]
