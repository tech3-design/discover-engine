from pydantic import BaseModel, HttpUrl


class DiscoverRequest(BaseModel):
    url: HttpUrl
