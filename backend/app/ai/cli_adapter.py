"""
CLI subprocess adapter for AI generation.

Spawns local CLI tools (claude, codex, gemini) as async subprocesses,
pipes the prompt via stdin or arguments, and captures stdout as the response.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from app.config import get_settings

from .adapter import AIAdapter, AIRequest, AIResponse

logger = logging.getLogger(__name__)


def _build_claude_args(request: AIRequest) -> list[str]:
    """Build command-line arguments for the Claude CLI."""
    args: list[str] = [
        "--print",
        "--output-format",
        "text",
        "--max-tokens",
        str(request.max_tokens),
    ]
    if request.system_prompt:
        args.extend(["--system-prompt", request.system_prompt])
    if request.response_schema:
        args.extend(["--output-format", "json"])
    return args


def _build_codex_args(request: AIRequest) -> list[str]:
    """Build command-line arguments for the Codex CLI."""
    args: list[str] = [
        "--quiet",
    ]
    if request.system_prompt:
        args.extend(["--instructions", request.system_prompt])
    return args


def _build_gemini_args(request: AIRequest) -> list[str]:
    """Build command-line arguments for the Gemini CLI."""
    args: list[str] = []
    if request.system_prompt:
        args.extend(["--system", request.system_prompt])
    return args


CLI_CONFIGS: dict[str, dict[str, Any]] = {
    "claude": {
        "command": "claude",
        "args_builder": _build_claude_args,
        "version_flag": "--version",
        "prompt_via": "positional",
    },
    "codex": {
        "command": "codex",
        "args_builder": _build_codex_args,
        "version_flag": "--version",
        "prompt_via": "positional",
    },
    "gemini": {
        "command": "gemini",
        "args_builder": _build_gemini_args,
        "version_flag": "--version",
        "prompt_via": "positional",
    },
}


class CLIAdapter(AIAdapter):
    """AI adapter that shells out to a local CLI tool."""

    def __init__(self) -> None:
        settings = get_settings()
        self._tool_name: str = settings.AI_CLI_TOOL
        self._timeout: int = settings.AI_CLI_TIMEOUT

        if self._tool_name not in CLI_CONFIGS:
            logger.warning(
                "Unknown CLI tool '%s'; falling back to claude",
                self._tool_name,
            )
            self._tool_name = "claude"

        self._config = CLI_CONFIGS[self._tool_name]

    async def generate(self, request: AIRequest) -> AIResponse:
        """Run the CLI tool and return the raw text response."""
        full_prompt = request.build_full_prompt()
        stdout, stderr, elapsed_ms = await self._run_subprocess(request, full_prompt)

        if stderr:
            logger.debug(
                "CLI stderr from %s: %s",
                self._tool_name,
                stderr[:500],
            )

        return AIResponse(
            content=stdout.strip(),
            model=f"cli:{self._tool_name}",
            adapter="cli",
            latency_ms=elapsed_ms,
        )

    async def generate_structured(self, request: AIRequest) -> AIResponse:
        """Run the CLI tool and parse the response as JSON."""
        if request.response_schema is None:
            request = request.model_copy(update={"response_schema": {"type": "object"}})

        response = await self.generate(request)

        # Validate that the output is parseable JSON
        try:
            response.parse_json()
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "CLI adapter produced non-JSON output: %s",
                response.content[:200],
            )
            raise ValueError(
                f"CLI tool '{self._tool_name}' did not return valid JSON: {exc}"
            ) from exc

        return response

    async def health_check(self) -> bool:
        """Check if the CLI tool is available by running its version command."""
        cmd = self._config["command"]
        version_flag = self._config["version_flag"]

        try:
            proc = await asyncio.create_subprocess_exec(
                cmd,
                version_flag,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10.0)
            if proc.returncode == 0:
                version_str = stdout.decode().strip().split("\n")[0]
                logger.info(
                    "CLI tool '%s' is available: %s",
                    self._tool_name,
                    version_str,
                )
                return True
            logger.warning(
                "CLI tool '%s' returned exit code %d: %s",
                self._tool_name,
                proc.returncode,
                stderr.decode()[:200],
            )
            return False
        except FileNotFoundError:
            logger.warning("CLI tool '%s' not found on PATH", self._tool_name)
            return False
        except TimeoutError:
            logger.warning("CLI tool '%s' version check timed out", self._tool_name)
            return False
        except Exception:
            logger.exception("Unexpected error checking CLI tool '%s'", self._tool_name)
            return False

    async def _run_subprocess(
        self,
        request: AIRequest,
        prompt: str,
    ) -> tuple[str, str, float]:
        """Spawn the CLI tool as an async subprocess and capture output.

        Returns:
            Tuple of (stdout, stderr, elapsed_ms).

        Raises:
            RuntimeError: If the process exits with a non-zero code or times out.
        """
        cmd = self._config["command"]
        args_builder = self._config["args_builder"]
        cli_args: list[str] = args_builder(request)

        # Build the full command
        full_cmd: list[str] = [cmd, *cli_args]

        if self._config["prompt_via"] == "positional":
            full_cmd.append(prompt)

        logger.debug(
            "Spawning CLI: %s (timeout=%ds)",
            " ".join(full_cmd[:3]) + " ...",
            self._timeout,
        )

        start = time.perf_counter()

        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(self._timeout),
            )

        except TimeoutError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "CLI tool '%s' timed out after %ds",
                self._tool_name,
                self._timeout,
            )
            # Attempt to kill the hanging process
            try:
                proc.kill()  # type: ignore[possibly-undefined]
                await proc.wait()  # type: ignore[possibly-undefined]
            except Exception:
                pass
            raise RuntimeError(
                f"CLI tool '{self._tool_name}' timed out after {self._timeout}s"
            ) from None

        except FileNotFoundError:
            raise RuntimeError(
                f"CLI tool '{self._tool_name}' not found. "
                f"Ensure '{cmd}' is installed and on PATH."
            ) from None

        elapsed_ms = (time.perf_counter() - start) * 1000

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        if proc.returncode != 0:
            logger.error(
                "CLI tool '%s' exited with code %d. stderr: %s",
                self._tool_name,
                proc.returncode,
                stderr[:500],
            )
            raise RuntimeError(
                f"CLI tool '{self._tool_name}' failed (exit code {proc.returncode}): "
                f"{stderr[:300]}"
            )

        logger.info(
            "CLI call completed in %.0fms (stdout=%d bytes)",
            elapsed_ms,
            len(stdout),
        )

        return stdout, stderr, elapsed_ms
