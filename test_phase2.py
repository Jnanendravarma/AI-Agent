import sys
import os
from engine.command_executor import CommandExecutor

def test():
    print("=" * 60)
    print("         PHASE 2 AUTOMATION INTEGRATION TESTS")
    print("=" * 60)
    
    # Initialize Command Executor (runs discovery & folder loading)
    print("Initializing Command Executor...")
    executor = CommandExecutor()
    
    # 1. Dynamic Application Discovery
    print("\n1. [Dynamic Application Discovery]")
    print(f"Discovered {len(executor.discovered_apps)} installed applications.")
    if executor.discovered_apps:
        sample_apps = list(executor.discovered_apps.keys())[:5]
        print(f"Sample discovered applications: {sample_apps}")
    else:
        print("No installed applications discovered (check Start Menu shortcut paths).")

    # 2. Smart Command Matching & Fuzzy Spelling Suggestion
    print("\n2. [Smart Matching & Spelling Suggestions]")
    test_queries = ["open chorme", "launch notepad", "start paint", "volume 40"]
    for q in test_queries:
        print(f"Testing fuzzy suggestion for '{q}':")
        success, resp = executor.execute(q)
        print(f" -> Success: {success} | Response: \"{resp}\"")

    # 3. System Controls
    print("\n3. [System Controls (Volume & Brightness)]")
    vol_queries = ["mute volume", "unmute volume", "set volume to 25 percent", "increase volume"]
    for v_q in vol_queries:
        print(f"Testing volume command '{v_q}':")
        success, resp = executor.execute(v_q)
        print(f" -> Success: {success} | Response: \"{resp}\"")

    bright_queries = ["set brightness to 60 percent", "increase brightness"]
    for b_q in bright_queries:
        print(f"Testing brightness command '{b_q}':")
        success, resp = executor.execute(b_q)
        print(f" -> Success: {success} | Response: \"{resp}\"")

    # 4. Battery and Diagnostics
    print("\n4. [Battery and Diagnostics]")
    diag_queries = ["battery status", "cpu usage", "ram usage", "disk space", "pc specs", "temperature status"]
    for d_q in diag_queries:
        print(f"Testing diagnostics command '{d_q}':")
        success, resp = executor.execute(d_q)
        print(f" -> Success: {success} | Response: \"{resp}\"")

    # 5. Persistent Command History
    print("\n5. [Command History Persistence]")
    success, resp = executor.execute("show history")
    print(f" -> Success: {success} | Response: \"{resp}\"")
    
    print("\n" + "=" * 60)
    print("                    TEST SUITE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test()
