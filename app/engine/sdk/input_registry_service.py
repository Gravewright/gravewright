"""Input commands: declarative commands and their user-owned bindings.

A package declares what a command means; the user owns which key invokes it.
Executing a command runs the package intent under the caller's authority.
"""

from __future__ import annotations

import json
import re

from app.engine.rules.declarative_action_service import DeclarativeActionService
from app.persistence.repositories.input_binding_repository import InputBindingRepository
from app.persistence.repositories.semantic_registration_repository import SemanticRegistrationRepository

from app.engine.sdk.semantic_authority import ACTION_REFERENCE, IDENTIFIER, SemanticResult

class InputRegistryService:
    CONTEXTS={"global","scene","actor-sheet","package-application","combat","text-input","text-input-excluded"};GESTURES={"tap","double-tap","long-press","drag","pan","cancel"}
    RESERVED={"Ctrl+L","Ctrl+T","Ctrl+W","Ctrl+N","Ctrl+R","Ctrl+Shift+T","Alt+F4","F5","F12"}
    MAX_ACTION_INPUT_BYTES=4_096
    def __init__(self):self.reg=SemanticRegistrationRepository();self.bindings=InputBindingRepository()
    def register(self,*,campaign_id,package_id,kind,definition):
        try:
            entry=str(definition.get("id") or "");registry="input-command" if kind=="command" else "input-gesture"
            if not IDENTIFIER.fullmatch(entry):raise ValueError
            if kind=="command":
                contexts=definition.get("contexts",["global"])
                if not isinstance(contexts,list) or any(c not in self.CONTEXTS for c in contexts):raise ValueError
                reference=str(definition.get("registeredAction") or "")
                # A command may be local-only (delivered to the package handler) or
                # server-bound; only a server-bound command may pre-bind action input.
                if reference:
                    action=ACTION_REFERENCE.fullmatch(reference)
                    if not action or action.group(1)!=package_id:raise ValueError
                elif "actionInput" in definition:raise ValueError
                if "actionInput" in definition:definition={**definition,"actionInput":self._action_input(definition.get("actionInput"))}
            elif kind=="gesture":
                if definition.get("gesture") not in self.GESTURES or not IDENTIFIER.fullmatch(str(definition.get("commandId") or "")):raise ValueError
            else:raise ValueError
            row=self.reg.put(campaign_id,package_id,registry,entry,definition);return SemanticResult(True,{"id":entry,"packageId":package_id,**row["definition"]})
        except (TypeError,ValueError):return SemanticResult(False,error_key="sdk.input.invalid_definition")
    def _action_input(self,value):
        """Pre-bound action input is package-definition data: bounded, plain JSON."""
        if not isinstance(value,dict):raise ValueError
        encoded=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":"),sort_keys=True)
        if len(encoded.encode())>self.MAX_ACTION_INPUT_BYTES:raise ValueError
        return json.loads(encoded)
    def list_commands(self,*,campaign_id,package_id):return SemanticResult(True,[{"id":r["entry_id"],"packageId":r["package_id"],**r["definition"]} for r in self.reg.list(campaign_id,"input-command",package_id)])
    def execute(self,*,campaign_id,user_id,package_id,command_id,inputs):
        row=self.reg.get(campaign_id,package_id,"input-command",command_id)
        if not row:return SemanticResult(False,error_key="sdk.input.command_not_found")
        definition=row["definition"];reference=str(definition.get("registeredAction") or "")
        # A local-only command has nothing for the server to run; saying so beats
        # failing later inside an action the package never referenced.
        if not reference:return SemanticResult(False,error_key="sdk.input.command_not_executable")
        # Pre-bound input is canonical: a caller may not substitute its own payload.
        if "actionInput" in definition:
            if inputs:return SemanticResult(False,error_key="sdk.input.action_input_not_allowed")
            resolved=definition["actionInput"]
        else:resolved=inputs if isinstance(inputs,dict) else {}
        match=ACTION_REFERENCE.fullmatch(reference);result=DeclarativeActionService().execute(campaign_id=campaign_id,user_id=user_id,package_id=match.group(1),action_id=match.group(2),version=int(match.group(3)),inputs=resolved)
        return SemanticResult(result.success,result.value,result.error_key)
    def get_bindings(self,*,user_id):return SemanticResult(True,self.bindings.list(user_id))
    def set_binding(self,*,campaign_id,user_id,package_id,command_id,binding,expected_version=None):
        if not self.reg.get(campaign_id,package_id,"input-command",command_id):return SemanticResult(False,error_key="sdk.input.command_not_found")
        if not isinstance(binding,str) or binding in self.RESERVED or not re.fullmatch(r"(?:(?:Ctrl|Alt|Shift|Meta)\+){0,3}(?:[A-Z0-9]|F(?:[1-9]|1[0-2]))",binding):return SemanticResult(False,error_key="sdk.input.binding_reserved")
        row=self.bindings.set(user_id,package_id,command_id,binding,expected_version)
        return SemanticResult(bool(row),row,None if row else "sdk.input.binding_conflict")
