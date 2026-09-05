import pytest
from runtime_core.interface_gateway import InterfaceGateway
from runtime_core.command_router import CommandRouter

class DummyRegistry:
    def get(self, key):
        if key == "thesis_pipeline_manager":
            class DummyPipeline:
                def request_human_approval(self, target, context):
                    return "token-123"
            return DummyPipeline()
        return None

def test_wake_word_parsing():
    interface = InterfaceGateway()
    
    # Text input
    assert interface.process_text_input("do something") == "do something"
    
    # Voice stream without wake word
    assert interface.process_voice_stream("ambient noise here") is None
    
    # Voice stream with wake word
    assert interface.process_voice_stream("Hey JARVIS compile thesis") == "compile thesis"
    
    # PTT overrides wake word
    interface.enable_push_to_talk(True)
    assert interface.process_voice_stream("just compile it") == "just compile it"

def test_command_router_thesis_export():
    router = CommandRouter(DummyRegistry())
    result = router.route_command("Hey JARVIS, export my thesis please")
    assert result["action"] == "require_approval"
    assert result["subsystem"] == "ThesisPipeline"
    assert result["token"] == "token-123"

def test_command_router_health():
    router = CommandRouter(DummyRegistry())
    result = router.route_command("What is your health status?")
    assert result["action"] == "system_status"
