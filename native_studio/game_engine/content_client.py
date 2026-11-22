"""Managed Qt transport selecting the typed chapter owner capability."""
from .creator_client import CreatorClient
from .content_commands import command_revision
from .project_assets import validate_asset_profile
from .workshop_fields import WORKSHOP_CAPABILITY,require_workshop_host

class ContentClient(CreatorClient):
    def __init__(self,parent=None,request_timeout_ms=60000,close_timeout_ms=3000):
        super().__init__(parent,request_timeout_ms,close_timeout_ms,
                         required_capability='chapter-authoring-v1',edit_revision=command_revision)
        self.asset_profile='legacy_v1'
        self.opening_workshop=False

    def _hello_requirements(self):
        required=super()._hello_requirements()
        return required|{WORKSHOP_CAPABILITY} if self.opening_workshop else required

    def start(self,executable,workspace):
        # Static JSON preflight precedes QProcess construction; Hello checks again
        # before ready.emit(), so a stale capability file cannot trigger OPEN.
        require_workshop_host(executable,self.opening_workshop)
        return super().start(executable,workspace)

    def _launch_arguments(self,workspace):
        profile=validate_asset_profile(self.asset_profile)
        args=super()._launch_arguments(workspace)
        if profile=='warm-beginning':args+=['--asset-profile',profile]
        return args
