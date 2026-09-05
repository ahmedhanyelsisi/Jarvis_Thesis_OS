import sys
import os

from .bootloader import JarvisBootloader

def print_dashboard(status_report: str):
    """Minimal ASCII Terminal Dashboard for Health Monitoring."""
    border = "=" * 50
    print(f"\n{border}")
    print(f"{'JARVIS THESIS OS - SYSTEM HEALTH':^50}")
    print(f"{border}")
    for line in status_report.split("\n"):
        print(f"| {line:<46} |")
    print(f"{border}\n")

def main():
    """Entry point for `jarvis start`."""
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    bootloader = JarvisBootloader(workspace_root)
    try:
        bootloader.boot()
    except Exception as e:
        print(f"[FATAL] Boot sequence failed: {e}")
        sys.exit(1)
        
    components = bootloader.get_runtime_components()
    health_monitor = components["health_monitor"]
    command_router = components["command_router"]
    interface = components["interface"]
    
    # Print the ASCII Dashboard
    print_dashboard(health_monitor.get_status_report())
    
    print("Type your command, or say 'Hey JARVIS' followed by your command.")
    print("Type 'exit' to shutdown.\n")
    
    while True:
        try:
            user_input = input("USER> ")
            if user_input.strip().lower() == "exit":
                break
                
            # Process via interface gateway (simulate hybrid text/voice)
            # If it starts with hey jarvis, it's processed as voice stream
            command = interface.process_voice_stream(user_input)
            if not command:
                # Fallback to pure text
                command = interface.process_text_input(user_input)
                
            # Route command
            result = command_router.route_command(command)
            
            if result["action"] == "system_status":
                print_dashboard(health_monitor.get_status_report())
            else:
                print(f"JARVIS> {result['message']}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"JARVIS> [ERROR] {str(e)}")
            
    print("\n[SHUTDOWN] Terminating JARVIS Runtime...")

if __name__ == "__main__":
    main()
