"""Validated configuration (YAML → Pydantic)."""

from __future__ import annotations

from typing import Optional, Tuple

from pydantic import BaseModel, Field, field_validator


_DEFAULT_PROTECTED_NAMES: Tuple[str, ...] = (
    "system",
    "system idle process",
    "idle",
    "csrss",
    "wininit",
    "services",
    "lsass",
    "smss",
    "svchost",
    "registry",
    "secure system",
    "fontdrvhost",
    "winlogon",
    "dwm",
)


class AgentSettings(BaseModel):
    """Runtime loop and buffer sizing."""

    tick_interval_seconds: float = Field(default=5.0, gt=0, le=3600)
    buffer_max_ticks: int = Field(default=120, ge=10, le=10_000)


class DiagnosisSettings(BaseModel):
    """Heuristic correlation of detection signals with metrics (P3: notify only)."""

    enabled: bool = True
    disk_io_high_bps: float = Field(
        default=5_000_000.0,
        gt=0,
        description="Sum of disk read+write above this ⇒ 'high disk' for correlation",
    )
    net_io_high_bps: float = Field(
        default=5_000_000.0,
        gt=0,
        description="Sum of net sent+recv above this ⇒ 'high network' for correlation",
    )


class DetectionSettings(BaseModel):
    """Thresholds for sustained conditions (P2: notify only)."""

    enabled: bool = True
    system_cpu_pct_above: Optional[float] = Field(default=85.0)
    system_cpu_sustained_ticks: int = Field(default=3, ge=1, le=500)
    memory_pct_above: Optional[float] = Field(default=90.0)
    memory_sustained_ticks: int = Field(default=3, ge=1, le=500)

    @field_validator("system_cpu_pct_above", "memory_pct_above", mode="before")
    @classmethod
    def empty_to_none(cls, v: object) -> object:
        if v is None or v == "":
            return None
        return v

    @field_validator("system_cpu_pct_above", "memory_pct_above")
    @classmethod
    def percent_range(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v < 0 or v > 100:
            raise ValueError("percent must be between 0 and 100")
        return v


class PolicySettings(BaseModel):
    """Safety gates for suggestions and process actions (P4)."""

    enabled: bool = True
    suggestions_enabled: bool = True
    soft_actions_enabled: bool = False
    hard_kill_enabled: bool = False
    min_confidence_for_soft: float = Field(default=0.48, ge=0, le=1)
    min_confidence_for_hard: float = Field(default=0.62, ge=0, le=1)
    min_cpu_share_for_soft: float = Field(default=10.0, ge=0, le=100)
    min_cpu_share_for_hard: float = Field(default=15.0, ge=0, le=100)
    protected_process_names: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_PROTECTED_NAMES),
    )
    hard_kill_max_per_window: int = Field(default=1, ge=1, le=10)
    hard_kill_cooldown_seconds: int = Field(default=3600, ge=60, le=86400)


class AppConfig(BaseModel):
    """Root config file shape."""

    version: int = 1
    agent: AgentSettings = Field(default_factory=AgentSettings)
    detection: DetectionSettings = Field(default_factory=DetectionSettings)
    diagnosis: DiagnosisSettings = Field(default_factory=DiagnosisSettings)
    policy: PolicySettings = Field(default_factory=PolicySettings)
