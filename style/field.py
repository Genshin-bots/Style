import asyncio
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Union, Any, Optional

import httpx
from PIL import Image


class BaseField(ABC):
    # Field常量
    # max_length, max_height,max_width...

    def __init__(self, value: Any) -> None:
        self._raw_value = value

    @abstractmethod
    def adjust() -> Any:
        ...


class TextField(BaseField):
    max_length = -1

    def __init__(self, value: str) -> None:
        super().__init__(value)

    def adjust(self) -> Any:
        if len(self._raw_value) != -1:
            if len(self._raw_value) >= self.max_length:
                return self._raw_value[:self.max_length]
        return self._raw_value


class ImageField(BaseField):
    _image: Image.Image
    max_width: int = -1
    max_height: int = -1

    async def _load_from_url(self) -> Union[Image.Image, None]:
        async with httpx.AsyncClient(follow_redirects=True) as _client:
            _resp: httpx.Response = await _client.get(self._raw_value)
            if _resp.status_code != 200:
                return None
            self._image = Image.open(BytesIO(_resp.read()))
        

    def __init__(self, value: Union[str, Path, httpx.URL, Image.Image]) -> None:
        super().__init__(value)
        if isinstance(value, str):
            if httpx.URL(value).scheme in ['http', 'https']:
                loop_ = asyncio.get_event_loop()
                loop_.run_until_complete(self._load_from_url())
            if Path(value).exists():
                value = Path(value)
        if isinstance(value, Path):
            self._image = Image.open(value.absolute())
        if isinstance(value, Image.Image):
            self._image = value

    def adjust(self, resize: Optional[bool] = False) -> Image.Image:
        width_ = self._image.width
        height_ = self._image.height

        if self.max_width < 0 and self.max_height < 0:
            return self._image
        if width_ == self.max_width and height_ == self.max_height:
            return self._image
        if width_ > self.max_width and height_ > self.max_height:
            if resize:
                return self._image.resize((self.max_width, self.max_height))
            return self._image.crop((0, 0, self.max_width, self.max_height))
        if resize:
            return self._image.resize((self.max_width, self.max_height))
        if width_ < self.max_width:
            return self._image.resize((self.max_width, int(self.max_width / width_ * height_))).crop((0, 0, self.max_width, self.max_height))
        return self._image.resize(
            (int(self.max_height / height_ * width_), self.max_height)).crop((0, 0, self.max_width, self.max_height))

    @property
    def show(self):
        return self.adjust().show

    @property
    def save(self):
        return self.adjust().save


class UIDField(TextField):
    max_length = 9
