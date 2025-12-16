from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Optional

import tinytuya

from .const import TUYA_PROTOCOL_VERSION


@dataclass
class ProscenicConfig:
    device_id: str
    local_key: str
    host: str
    protocol_version: float = TUYA_PROTOCOL_VERSION


class ProscenicApi:
    """Async wrapper over tinytuya."""

    def __init__(self, cfg: ProscenicConfig) -> None:
        self._cfg = cfg
        self._dev = self._build_device(cfg.host)

    def _build_device(self, host: str):
        dev = tinytuya.OutletDevice(self._cfg.device_id, host, self._cfg.local_key)
        try:
            dev.set_version(self._cfg.protocol_version)
        except Exception:
            dev.version = self._cfg.protocol_version  # type: ignore[attr-defined]
        return dev

    @property
    def device_id(self) -> str:
        return self._cfg.device_id

    @property
    def host(self) -> str:
        return self._cfg.host

    def update_host(self, host: str) -> None:
        """Rebuild underlying tinytuya device with a new host."""
        self._cfg.host = host
        self._dev = self._build_device(host)

    async def status(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._dev.status)

    async def set_dp(self, dp: int, value: Any) -> None:
        await asyncio.to_thread(self._dev.set_value, dp, value)


async def discover_ip_by_device_id(device_id: str, timeout_s: int = 8) -> Optional[str]:
    """
    Best-effort LAN discovery via tinytuya.deviceScan, matching gwId/id == device_id.
    """

    def _scan() -> dict[str, Any]:
        return tinytuya.deviceScan(maxretry=2, color=False)

    try:
        data = await asyncio.wait_for(asyncio.to_thread(_scan), timeout=timeout_s)
    except Exception:
        return None

    if not data:
        return None

    for ip_key, info in data.items():
        if not isinstance(info, dict):
            continue
        gwid = info.get("gwId") or info.get("id")
        if gwid == device_id:
            return info.get("ip") or ip_key

    return None