from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from threading import RLock
from typing import Any

import click


@dataclass(frozen=True)
class LogContext:
    scope: str | None = None
    label: str | None = None


_context: ContextVar[LogContext] = ContextVar(
    "harness_log_context", default=LogContext()
)
_log_lock = RLock()


def set_log_context(scope: str, label: str | None = None):
    return _context.set(LogContext(scope=scope, label=label))


def reset_log_context(token) -> None:
    _context.reset(token)


def log_kv(
    key: str,
    value: Any,
    *,
    limit: int = 220,
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        _print_agent_prefix(agent_name)
        _detail(key, _format_value(value, limit=limit))


def log_event(
    label: str,
    message: str,
    *,
    color: str = "cyan",
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        _line(f"[{label}]", message, fg=color, bold=True, agent_name=agent_name)


def log_tool_call_invoke(
    name: str,
    arguments: dict[str, Any],
    *,
    compact: bool = False,
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        _log_tool_call(name, arguments, compact=compact, agent_name=agent_name)


def log_tool_call_result(
    name: str,
    response: Any,
    *,
    compact: bool = False,
    max_lines: int | None = None,
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        if compact:
            preview = _shorten(str(response), 120)
            _print_agent_prefix(agent_name)
            click.secho("[tool output]", fg="green", bold=True, nl=False)
            click.secho(f" {name} ", fg="green", bold=True, nl=False)
            click.secho(preview, dim=True)
            return

        _line("[tool output]", name, fg="green", bold=True, agent_name=agent_name)
        effective_max_lines = max_lines if max_lines is not None else 30
        for line in _preview_lines(str(response), max_lines=effective_max_lines):
            click.secho(f"  {line}", dim=True)


def log_answer(
    answer: str,
    *,
    compact: bool = False,
    max_lines: int | None = None,
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        _print_agent_prefix(agent_name)
        click.secho("[answer]", fg="green", bold=True)
        effective_max_lines = max_lines if max_lines is not None else (8 if compact else 12)
        for line in _preview_lines(answer, max_lines=effective_max_lines):
            click.secho(line, fg="white")


def log_task_spawn(
    label: str,
    task: str,
    *,
    tools: list[str] | None = None,
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        _line("[task]", f"{label} spawned", fg="blue", bold=True, agent_name=agent_name)
        _print_agent_prefix(agent_name)
        _detail("task", _shorten(task, 180))
        if tools:
            _print_agent_prefix(agent_name)
            _detail("tools", ", ".join(tools))


def log_task_done(
    label: str,
    elapsed_seconds: float,
    *,
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        _line(
            f"[{label}]",
            f"done in {elapsed_seconds:.1f}s",
            fg="green",
            bold=True,
            agent_name=agent_name,
        )


def log_task_failed(
    label: str,
    elapsed_seconds: float,
    error: Exception,
    *,
    agent_name: str | None = None,
) -> None:
    with _log_lock:
        _line(
            f"[{label}]",
            f"failed in {elapsed_seconds:.1f}s",
            fg="red",
            bold=True,
            agent_name=agent_name,
        )
        _print_agent_prefix(agent_name)
        _detail("error", str(error))


def in_log_context() -> bool:
    context = _context.get()
    return context.scope is not None


def _log_tool_call(
    name: str,
    arguments: dict[str, Any],
    *,
    compact: bool,
    agent_name: str | None,
) -> None:
    context = _context.get()
    if context.scope:
        label = f"[{context.scope}{f' {context.label}' if context.label else ''}]"
        color = "blue"
    else:
        label = "[tool]"
        color = "cyan"

    if compact:
        _compact_line(label, name, arguments, fg=color, agent_name=agent_name)
        return

    _line(label, name, fg=color, bold=True, agent_name=agent_name)
    _arguments(arguments)


def _line(
    label: str,
    message: str,
    *,
    fg: str,
    bold: bool = False,
    dim: bool = False,
    agent_name: str | None = None,
) -> None:
    _print_agent_prefix(agent_name)
    click.secho(label, fg=fg, bold=bold, dim=dim, nl=False)
    click.echo(f" {message}")


def _arguments(arguments: dict[str, Any]) -> None:
    for key, value in arguments.items():
        _detail(key, _format_value(value, limit=220))


def _compact_line(
    label: str,
    name: str,
    arguments: dict[str, Any],
    *,
    fg: str,
    agent_name: str | None = None,
) -> None:
    _print_agent_prefix(agent_name)
    click.secho(label, fg=fg, bold=True, nl=False)
    click.secho(f" {name}", fg=fg, bold=True, nl=False)
    for key, value in arguments.items():
        click.echo(" ", nl=False)
        click.secho(f"{key}=", dim=True, nl=False)
        click.echo(_format_value(value, limit=80), nl=False)
    click.echo()


def _detail(key: str, value: Any) -> None:
    click.secho(f"  {key}: ", dim=True, nl=False)
    click.echo(value)


def _print_agent_prefix(agent_name: str | None) -> None:
    if agent_name:
        click.secho(f"[{agent_name}] ", fg="blue", bold=True, nl=False)


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
