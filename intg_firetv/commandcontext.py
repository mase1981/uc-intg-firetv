import contextvars
from dataclasses import dataclass, asdict

@dataclass
class CommandContext:
    command: str
    repeat: int
    delay: int
    hold: int
    key_down: bool

_current_command = contextvars.ContextVar("current_command")

def set_context(ctx: CommandContext):
    return _current_command.set(ctx)

def reset_context(token):
    _current_command.reset(token)

def get_context() -> CommandContext:
    return _current_command.get()

def serialize_context():
    return asdict(_current_command.get())
