"""Custom MCP server (FastMCP) for Homework 5.

Exposes the contents of ``lorem-ipsum.md`` to an MCP client (Claude Code)
through two complementary primitives:

* a **Resource** — a URI the client can *read* from, returning a configurable
  number of words from the source file;
* a **Tool** named ``read`` — an *action* the client can *call* to fetch the
  same word-limited content.

Resources vs. Tools (short version):
    - Resources are URIs Claude can read from (files, APIs, dynamic content).
      They are side-effect-free "GET-like" data sources.
    - Tools are actions Claude can call to *do* something (read a file,
      run a command, mutate state). They are "POST-like" operations.

Run with:  ``uv run server.py``  (stdio transport, the default for MCP clients)
"""

from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP("lorem-ipsum-server")

# The source file lives next to this script, so the server works regardless of
# the directory the MCP client launches it from.
SOURCE_FILE = Path(__file__).parent / "lorem-ipsum.md"

DEFAULT_WORD_COUNT = 30


def _read_words(word_count: int = DEFAULT_WORD_COUNT) -> str:
    """Return exactly ``word_count`` words from the lorem-ipsum source.

    Only the prose body is used (the leading ``# Lorem Ipsum Source`` heading
    is skipped) so the output is clean text. ``word_count`` is clamped to the
    range ``[1, total_words]`` to stay robust against bad input.
    """
    raw = SOURCE_FILE.read_text(encoding="utf-8")

    # Drop markdown heading lines so only the lorem prose is counted.
    body = " ".join(
        line for line in raw.splitlines() if not line.lstrip().startswith("#")
    )
    words = body.split()

    if word_count < 1:
        word_count = 1
    if word_count > len(words):
        word_count = len(words)

    return " ".join(words[:word_count])


@mcp.resource("lorem://words/{word_count}")
def lorem_resource(word_count: int = DEFAULT_WORD_COUNT) -> str:
    """Resource URI: ``lorem://words/{word_count}``.

    Reads from ``lorem-ipsum.md`` and returns the first ``word_count`` words
    (default ``30``). This is the read-only data source Claude can subscribe to.
    """
    return _read_words(word_count)


@mcp.tool
def read(word_count: int = DEFAULT_WORD_COUNT) -> str:
    """Return the first ``word_count`` words from ``lorem-ipsum.md``.

    Mirrors the ``lorem://words/{word_count}`` resource as a callable action.

    Args:
        word_count: How many words to return. Defaults to 30.
    """
    return _read_words(word_count)


if __name__ == "__main__":
    # Default transport is stdio — the transport MCP clients (Claude Code,
    # Copilot) use to launch and talk to a local server.
    mcp.run()
