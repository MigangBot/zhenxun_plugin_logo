import base64
import jinja2
import imageio
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Union, Protocol

from utils.migang.http import html_to_pic
from utils.http_utils import AsyncPlaywright


dir_path = Path(__file__).parent
template_path = dir_path / "templates"
path_url = f"file://{template_path.absolute()}"
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(template_path), enable_async=True
)


async def to_image(html: str) -> bytes:
    return await html_to_pic(
        html, viewport={"width": 100, "height": 100}, template_path=path_url
    )


async def make_pornhub(texts: List[str]) -> bytes:
    template = env.get_template("pornhub.html")
    html = await template.render_async(left_text=texts[0], right_text=texts[1])
    return await to_image(html)


async def make_youtube(texts: List[str]) -> bytes:
    template = env.get_template("youtube.html")
    html = await template.render_async(left_text=texts[0], right_text=texts[1])
    return await to_image(html)


async def make_5000choyen(texts: List[str]) -> str:
    template = env.get_template("5000choyen.html")
    html = await template.render_async(top_text=texts[0], bottom_text=texts[1])

    try:
        page = await AsyncPlaywright.goto(path_url)
        await page.set_content(html)
        await page.wait_for_selector("a")
        a = await page.query_selector("a")
        assert a
        img = await (await a.get_property("href")).json_value()
    finally:
        if page:
            await page.close()
    return "base64://" + str(img).replace("data:image/png;base64,", "")


async def make_douyin(texts: List[str]) -> BytesIO:
    template = env.get_template("douyin.html")
    html = await template.render_async(text=texts[0], frame_num=10)

    try:
        page = await AsyncPlaywright.goto(path_url)
        await page.set_content(html)
        imgs = await page.query_selector_all("a")
        imgs = [await (await img.get_property("href")).json_value() for img in imgs]
    finally:
        if page:
            await page.close()
    imgs = [
        imageio.imread(base64.b64decode(str(img).replace("data:image/png;base64,", "")))
        for img in imgs
    ]

    output = BytesIO()
    imageio.mimsave(output, imgs, format="gif", duration=0.2)
    return output


async def make_google(texts: List[str]) -> bytes:
    template = env.get_template("google.html")
    html = await template.render_async(text=texts[0])
    return await to_image(html)


class Func(Protocol):
    async def __call__(self, texts: List[str]) -> Union[str, bytes, BytesIO, Path]:
        ...


@dataclass
class Command:
    keywords: Tuple[str, ...]
    func: Func
    arg_num: int = 1


commands = [
    Command(("phlogo",), make_pornhub, 2),
    Command(("ytlogo",), make_youtube, 2),
    Command(("5000兆",), make_5000choyen, 2),
    Command(("dylogo",), make_douyin),
    Command(("gglogo",), make_google),
]
