"""Build the browser version of One Way Down with pygbag (Python and pygame compiled to WebAssembly), ready to upload
to itch.io as an HTML game.

Run (from the project folder):
    uv run --no-project --with pygbag --with soundfile --with numpy tools/build_web.py

Out:
    build/onewaydown/                         what pygbag builds from: the code, the fonts, the audio as .ogg
    tools/web/logo.png, tools/web/audio/      kept from build to build - commit them (see below)
    dist/OneWayDown-<version>-web.zip         upload this to itch.io, with "This file will be played in the browser"

To try it locally first, serve dist/web and open http://127.0.0.1:8001 - the number, NOT "localhost": on a page
called localhost, pygbag assumes its own development server is on port 8000 and looks there for pygame, finds nothing
and the page stays grey. (Add #debug to the address to see Python's output on the page if anything goes wrong.)
    uv run --no-project python -m http.server 8001 --bind 127.0.0.1 --directory dist/web

The page around the game - its loading screen, with the logo and "Click to start" - is tools/web/onewaydown.tmpl, a
copy of pygbag's own template (default.tmpl) restyled; the logo (tools/web/logo.png) and the font it uses are copied in
beside it.

What the build makes is kept in tools/web and committed, so it's remembered rather than remade each time: the logo,
redrawn from the game's own title on every build (git shows when it changes), and the audio as .ogg in tools/web/audio,
converted from a .wav only when there's no .ogg yet or the .wav is newer (so soundfile and numpy are only needed then).

In a browser the game keeps its saves and settings in the browser's own storage (see dig/storage.py), and plays the
.ogg audio made here (see config.AUDIO_EXT), through the browser's own mixer rather than pygame's
(see dig/webaudio.py).
"""
import os
import shutil
import subprocess
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "build", "onewaydown")   # (pygbag names the game after its folder)
DIST = os.path.join(ROOT, "dist")
WEB = os.path.join(ROOT, "tools", "web")
TEMPLATE = os.path.join(WEB, "onewaydown.tmpl")
LOGO = os.path.join(WEB, "logo.png")
AUDIO = os.path.join(WEB, "audio")   # (the .ogg of each .wav in assets/music and assets/sfx)


def version():
    with open(os.path.join(ROOT, "pyproject.toml"), "rb") as f:
        return tomllib.load(f)["project"]["version"]


def stage():
    """A clean copy of what the browser game needs: main.py, the dig package, the fonts, and the audio as Ogg."""
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(STAGE)
    shutil.copy(os.path.join(ROOT, "main.py"), STAGE)
    shutil.copytree(os.path.join(ROOT, "dig"), os.path.join(STAGE, "dig"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(os.path.join(ROOT, "assets", "fonts"), os.path.join(STAGE, "assets", "fonts"))
    oggs()
    for kind in ("music", "sfx"):
        shutil.copytree(os.path.join(AUDIO, kind), os.path.join(STAGE, "assets", kind))
    images()


def oggs():
    """Bring tools/web/audio up to date with the .wav files: convert any that are new or changed, and drop the .ogg of
    any .wav that's gone."""
    for kind in ("music", "sfx"):
        src, dst = os.path.join(ROOT, "assets", kind), os.path.join(AUDIO, kind)
        os.makedirs(dst, exist_ok=True)
        wavs = {name[:-4] for name in os.listdir(src) if name.endswith(".wav")}
        for name in sorted(wavs):
            wav, ogg = os.path.join(src, name + ".wav"), os.path.join(dst, name + ".ogg")
            if not os.path.exists(ogg) or os.path.getmtime(wav) > os.path.getmtime(ogg):
                import soundfile
                data, rate = soundfile.read(wav)
                soundfile.write(ogg, data, rate, format="OGG", subtype="VORBIS")
                print(f"Converted {kind}/{name}.wav")
        for name in os.listdir(dst):
            if name.endswith(".ogg") and name[:-4] not in wavs:
                os.remove(os.path.join(dst, name))
                print(f"Removed {kind}/{name} (its .wav is gone)")


def images():
    """The page's icon (the game's own, dig/appicon.py), and for the loading screen the title logo as the menu draws
    it, cropped, plus the font its text is in."""
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    sys.path.insert(0, ROOT)
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    from dig.appicon import make_icon
    from dig.title import Title
    pygame.image.save(pygame.transform.smoothscale(make_icon(), (64, 64)), os.path.join(STAGE, "favicon.png"))
    logo = pygame.Surface((1280, 520), pygame.SRCALPHA)
    Title(1280).draw(logo, 640, 20, 1.0)
    pygame.image.save(logo.subsurface(logo.get_bounding_rect()), LOGO)


def build():
    subprocess.run([sys.executable, "-m", "pygbag", "--build", "--archive", "--title", "One Way Down",
                    "--template", TEMPLATE, STAGE], check=True)
    web = os.path.join(STAGE, "build", "web")
    shutil.copy(LOGO, web)   # (served beside the page, kept out of the game's own archive)
    shutil.copy(os.path.join(ROOT, "assets", "fonts", "LilitaOne-Regular.ttf"), os.path.join(web, "lilita.ttf"))
    os.makedirs(DIST, exist_ok=True)
    shutil.rmtree(os.path.join(DIST, "web"), ignore_errors=True)
    shutil.copytree(web, os.path.join(DIST, "web"))   # (to serve and try)
    out = os.path.join(DIST, f"OneWayDown-{version()}-web")
    shutil.make_archive(out, "zip", web)
    print(f"\nBuilt {os.path.join(DIST, 'web')}\nZipped {out}.zip  (upload to itch.io as a browser game)")


if __name__ == "__main__":
    stage()
    build()
