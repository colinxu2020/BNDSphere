from typing import Annotated

from pydantic import AfterValidator, HttpUrl

UrlString = Annotated[HttpUrl, AfterValidator(str)]
