
from typing import Optional

class GeneralException(Exception):
    """
    Custom exception class for handling errors related to exposures.
    """
    def __init__(self, message: str, id: Optional[str] = None):
        """
        Initialize the exception with an error message and optional exposure ID.

        Args:
            message (str): The error message describing the exception.
            exposure_id (str, optional): The ID of the exposure related to the error.
        """
        self.message = message
        self.id = id
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """
        Format the exception message to include the exposure ID if provided.

        Returns:
            str: The formatted exception message.
        """
        if self.id:
            return f"ExposureException: {self.message} (Exposure ID: {self.id})"
        return f"ExposureException: {self.message}"
    

class ExposureException(GeneralException):
    def __init__(self, message: str, exposure_id: Optional[str] = None):
        super().__init__(message, exposure_id)


class ClaimsException(GeneralException):
    def __init__(self, message: str, claim_id: Optional[str] = None):
        super().__init__(message, claim_id)

# ExposureException(
#                 "Exposure period start date cannot be after the end date.",
#                 exposure_id=exposure_meta.exposure_id
#             )

# ClaimsException(
#                     "Policy inception date is required for UNDERWRITING_YEAR modelling.",
#                     claim_id=self.claim_id
#                 )