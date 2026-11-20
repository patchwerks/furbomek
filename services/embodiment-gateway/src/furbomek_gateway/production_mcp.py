"""Opt-in typed production tools; no default enrollment or physical permit."""

import json
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import BeforeValidator, JsonValue

from .edge_protocol import EdgeReply, exchange, unix_ms
from .motion_sequence_models import SequenceRequest
from .production_control import (
    Movement,
    OwnerOperation,
    PresetApply,
    ProductionRequest,
    ReactionOperation,
    SourceDelivery,
    Status,
)
from .production_http_models import ACTION, OwnerAction
from .production_sources.contracts import SourceReceipt


def parse_owner_action(value: JsonValue) -> OwnerAction:
    """Restore JSON-array semantics before strict DTO validation by FastMCP."""
    return ACTION.validate_json(json.dumps(value))


def parse_movement(value: JsonValue) -> SequenceRequest:
    """Parse the wire JSON, preserving strict scalars and finite tuple bounds."""
    return SequenceRequest.model_validate_json(json.dumps(value))


def register_production_tools(server: FastMCP, socket: Path) -> None:
    """Register one shared semantic state and closed operations over the edge."""

    @server.tool(structured_output=True)
    async def production_status() -> EdgeReply:
        """Read observed media state, catalog and production stage HOLD."""
        return await exchange(
            socket, ProductionRequest(issued_ms=unix_ms(), operation=Status())
        )

    @server.resource("furbomek://production/catalog")
    async def production_catalog() -> str:
        """Return the same live catalog and held stage as the private owner API."""
        reply = await exchange(
            socket, ProductionRequest(issued_ms=unix_ms(), operation=Status())
        )
        return reply.model_dump_json(exclude_none=True)

    @server.tool(structured_output=True)
    async def production_effect(
        request: Annotated[OwnerAction, BeforeValidator(parse_owner_action)],
    ) -> EdgeReply:
        """Preview/apply/revert or save bounded effects with epoch/revision CAS."""
        return await exchange(
            socket,
            ProductionRequest(
                issued_ms=unix_ms(), operation=OwnerOperation(request=request)
            ),
        )

    @server.tool(structured_output=True)
    async def production_preset(epoch: str, revision: int) -> EdgeReply:
        """Apply saved typed effects; saved configuration is never authorization."""
        return await exchange(
            socket,
            ProductionRequest(
                issued_ms=unix_ms(),
                operation=PresetApply(epoch=epoch, revision=revision),
            ),
        )

    @server.tool(structured_output=True)
    async def production_reaction(request: ReactionOperation) -> EdgeReply:
        """Preview/trigger a configured pack or cancel/read its private schedule."""
        return await exchange(
            socket, ProductionRequest(issued_ms=unix_ms(), operation=request)
        )

    @server.tool(structured_output=True)
    async def production_source(receipt: SourceReceipt) -> EdgeReply:
        """Deliver curated source events only when this transport is enrolled."""
        return await exchange(
            socket,
            ProductionRequest(
                issued_ms=unix_ms(), operation=SourceDelivery(receipt=receipt)
            ),
        )

    @server.tool(structured_output=True)
    async def production_movement(
        request: Annotated[SequenceRequest, BeforeValidator(parse_movement)],
    ) -> EdgeReply:
        """Submit bounded intent; stage mode is HOLD without a local release permit."""
        return await exchange(
            socket,
            ProductionRequest(issued_ms=unix_ms(), operation=Movement(request=request)),
        )
