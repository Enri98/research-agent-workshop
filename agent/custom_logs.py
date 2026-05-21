from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

import click


@dataclass(frozen=True)
class LogContext:
    subagent_id: int | None = None
    task: str | None = None


_context: ContextVar[LogContext] = ContextVar("agent_log_context", default=LogContext())


def set_subagent_context(subagent_id: int, task: str):
    return _context.set(LogContext(subagent_id=subagent_id, task=task))


def reset_context(token) -> None:
    _context.reset(token)


def log_tool_call(name: str, **arguments: Any) -> None:
    context = _context.get()
    if context.subagent_id is None:
        _line("[tool]", name, fg="cyan", bold=True)
        _arguments(arguments)
        return

    _line(
        f"[subagent S{context.subagent_id}]",
        name,
        fg="blue",
        bold=True,
    )
    _arguments(arguments, compact=True)


def log_tool_output(name: str, output: str) -> None:
    context = _context.get()
    if context.subagent_id is not None:
        return

    _line("[tool output]", name, fg="green", bold=True)
    for line in _preview_lines(output):
        click.secho(f"  {line}", dim=True)


def log_delegate_start(task_count: int, max_parallel: int, concurrency: int) -> None:
    _line(
        "[delegate]", f"starting {task_count} research task(s)", fg="magenta", bold=True
    )
    _detail("parallelism", f"{concurrency}/{max_parallel}")


def log_delegate_task(index: int, task: str) -> None:
    _detail(f"task S{index}", _shorten(task, 180))


def log_subagent_spawn(index: int, task: str) -> None:
    _line("[subagent]", f"S{index} spawned", fg="blue", bold=True)
    _detail("task", _shorten(task, 180))
    _detail("tools", "search")


def log_subagent_done(index: int, elapsed_seconds: float) -> None:
    _line(
        f"[subagent S{index}]",
        f"done in {elapsed_seconds:.1f}s",
        fg="green",
        bold=True,
    )


def log_subagent_response(index: int, response: str) -> None:
    _line(f"[subagent S{index}]", "response", fg="green", bold=True)
    for line in _preview_lines(response, max_lines=8, line_limit=180):
        click.secho(f"  {line}", dim=True)


def log_subagent_failed(index: int, elapsed_seconds: float, error: Exception) -> None:
    _line(
        f"[subagent S{index}]",
        f"failed in {elapsed_seconds:.1f}s",
        fg="red",
        bold=True,
    )
    _detail("error", str(error))


def _line(
    label: str,
    message: str,
    *,
    fg: str,
    bold: bool = False,
    dim: bool = False,
) -> None:
    click.secho(label, fg=fg, bold=bold, dim=dim, nl=False)
    click.echo(f" {message}")


def _arguments(arguments: dict[str, Any], *, compact: bool = False) -> None:
    if compact:
        rendered = " ".join(
            f"{key}={_format_value(value, limit=80)}"
            for key, value in arguments.items()
        )
        click.secho(f"  {rendered}", dim=True)
        return

    for key, value in arguments.items():
        _detail(key, _format_value(value, limit=220))


def _detail(key: str, value: Any) -> None:
    click.secho(f"  {key}: ", dim=True, nl=False)
    click.echo(value)


def _format_value(value: Any, *, limit: int) -> str:
    if isinstance(value, str):
        return f'"{_shorten(value, limit)}"'
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "null"
    if isinstance(value, list):
        return f"[{len(value)} item(s)]"
    return _shorten(str(value), limit)


def _shorten(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _preview_lines(
    value: str,
    *,
    max_lines: int = 30,
    line_limit: int = 180,
) -> list[str]:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    preview = [_shorten(line, line_limit) for line in lines[:max_lines]]
    if len(lines) > max_lines:
        preview.append(f"... {len(lines) - max_lines} more line(s)")
    return preview
