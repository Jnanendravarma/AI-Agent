import os
import sys
import time
from engine.command_executor import CommandExecutor
from utils.logger import logger
from ai.intent_classifier import IntentClassifier
from ai.gemini_client import GeminiClient
from google.genai.errors import APIError

def run_tests():
    print("=" * 60)
    print("         PHASE 3 INTEGRATION AND UX TESTS")
    print("=" * 60)

    # 1. Initialize Executor & check SDK Client
    print("\n1. [Gemini Client and SDK Model Selection]")
    executor = CommandExecutor()
    client = executor.gemini_client
    print(f"Client Initialized: {client.client_initialized}")
    print(f"Default Auto-selected Model: {client.default_model}")

    # 2. Local Intent Classification Checks (No Gemini Calls)
    print("\n2. [Local Intent Classifier Verb & App Priority]")
    classifier = executor.intent_classifier
    
    test_cases = [
        ("open chrome", "open_application", "chrome"),
        ("close chrome", "close_application", "chrome"),
        ("chrome open chey", "open_application", "chrome"),
        ("chrome band karo", "close_application", "chrome"),
        ("open vs code", "open_application", "vscode"),
        ("close vscode", "close_application", "vscode"),
        ("volume 50", "volume_control", ""),
        ("volume penchu", "volume_control", ""),
        ("battery status", "system_control", ""),
        ("what is machine learning", "chat_mode", ""),
    ]

    local_matching_success = True
    for text, expected_intent, expected_app in test_cases:
        res = classifier.classify_locally(text)
        intent = res.get("intent")
        app = res.get("entities", {}).get("app_name", "")
        
        # Standardize vscode name checking
        if expected_app == "vscode" and app in ["vs code", "vscode", "visual studio code"]:
            app_match = True
        else:
            app_match = (app == expected_app)

        if intent == expected_intent and app_match:
            print(f" -> PASS: '{text}' matched intent: {intent} (app: {app})")
        else:
            print(f" -> FAIL: '{text}' got intent: {intent} (app: {app}), expected: {expected_intent} (app: {expected_app})")
            local_matching_success = False

    # 3. Hybrid Command Orchestration and Mode Separation
    print("\n3. [Hybrid Automation vs AI Chat Mode]")
    # Verify starting in Automation Mode
    print(f"Active Chat Mode: {executor.in_chat_mode} (Should be False)")
    
    # Run conversational command in Automation Mode (Should reject without Gemini call)
    print("Running conversational query in Automation Mode:")
    success, resp = executor.execute("Teach me React Hooks")
    print(f" -> Success: {success} | Response: \"{resp}\"")
    
    # Toggle Chat Mode On
    print("Sending 'start chat mode':")
    success, resp = executor.execute("start chat mode")
    print(f" -> Success: {success} | Response: \"{resp}\"")
    print(f"Active Chat Mode: {executor.in_chat_mode} (Should be True)")
    
    # Toggle Chat Mode Off
    print("Sending 'exit chat mode':")
    success, resp = executor.execute("exit chat mode")
    print(f" -> Success: {success} | Response: \"{resp}\"")
    print(f"Active Chat Mode: {executor.in_chat_mode} (Should be False)")

    # 4. Logger Verification
    print("\n4. [Logger and Performance Metrics]")
    log_path = "logs/assistant.log"
    if os.path.exists(log_path):
        print(f"Log file exists at {log_path}. Printing last 15 lines of log:")
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-15:]:
                print("   " + line.strip())
    else:
        print("FAIL: logs/assistant.log was not created.")

    # 5. Gemini 429 Retry Cutoff Verification
    print("\n5. [Gemini 429 Quota Exhaustion Retry Cutoff]")
    print("Testing simulated APIError (429 Resource Exhausted)...")
    
    # Create a mock APIError for 429
    class MockAPIError(APIError):
        def __init__(self):
            super().__init__(code=429, response_json={"error": {"code": 429, "message": "Simulated RESOURCE_EXHAUSTED error"}}, response=None)
            
    # Temporarily monkey-patch the client models.generate_content to raise 429
    if client.client:
        original_gen = client.client.models.generate_content
        def mock_generate(*args, **kwargs):
            raise MockAPIError()
        client.client.models.generate_content = mock_generate
        
        try:
            # Attempt a call
            res, err = client.generate_content("test query", retries=3)
            print(f" -> Response: {res} | Error: \"{err}\"")
            if err == "AI service is busy. Please try again after a minute.":
                print(" -> PASS: Correctly aborted retries and returned busy message on 429.")
            else:
                print(f" -> FAIL: Unexpected error returned: {err}")
        finally:
            # Restore original method
            client.client.models.generate_content = original_gen
    else:
        print("Skipped 429 test: Gemini client not initialized.")

    print("\n" + "=" * 60)
    print("                  TEST SUITE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
