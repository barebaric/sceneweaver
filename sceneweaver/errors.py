class ValidationError(ValueError):
    """
    Custom exception for errors related to invalid specification files.
    """

    pass


class TemplateNotFoundError(ValueError):
    """
    Custom exception for when a specified template cannot be found.
    """

    pass
