from pathlib import Path
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .common import ConflictError
from .master import Master


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MasterStart(Input):
    scenario: Literal["standard", "clean"] = "standard"


class MasterAction(Input):
    revision: int = Field(ge=1)
    action: Literal["approve", "reject", "publish", "replay"]
    pair_id: str = Field(default="", max_length=120)


def router(root: Path) -> APIRouter:
    routes = APIRouter(prefix="/api/labs", tags=["Independent solution demonstrations"])
    master = Master(root)

    def identity(value: str | None, allowed: set[str]) -> str:
        if value not in allowed:
            raise HTTPException(401, "Select a valid simulated lab identity")
        return value

    def call(function: Any, *args: Any) -> dict[str, Any]:
        try:
            return cast(dict[str, Any], function(*args))
        except ConflictError as error:
            raise HTTPException(409, str(error)) from error
        except PermissionError as error:
            raise HTTPException(403, str(error)) from error
        except LookupError as error:
            raise HTTPException(404, str(error)) from error
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    @routes.post("/master/runs")
    def start_master(
        body: MasterStart, x_demo_identity: Annotated[str | None, Header()] = None
    ) -> dict[str, Any]:
        owner = identity(x_demo_identity, {"steward", "viewer"})
        return call(master.create, body.scenario, owner)

    @routes.get("/master/runs/{key}")
    def load_master(
        key: str, x_demo_identity: Annotated[str | None, Header()] = None
    ) -> dict[str, Any]:
        return call(master.load, key, identity(x_demo_identity, {"steward", "viewer"}))

    @routes.post("/master/runs/{key}/actions")
    def master_action(
        key: str, body: MasterAction, x_demo_identity: Annotated[str | None, Header()] = None
    ) -> dict[str, Any]:
        return call(
            master.action,
            key,
            identity(x_demo_identity, {"steward", "viewer"}),
            body.revision,
            body.action,
            body.pair_id,
        )

    return routes
