import re
from plugins.base_plugin import BasePlugin

class CalculatorPlugin(BasePlugin):
    def get_keywords(self) -> list[str]:
        return ["calculate", "plus", "minus", "multiplied by", "divided by", "times", "what is the sum of", "solve math"]

    def execute(self, command: str) -> tuple[bool, str]:
        cmd_lower = command.lower().strip()
        
        # Clean prefix text
        expr = cmd_lower
        prefixes = ["calculate", "solve math", "what is the sum of", "what is", "solve"]
        for p in prefixes:
            if expr.startswith(p):
                expr = expr[len(p):].strip()
                
        # Handle word-based operations
        expr = expr.replace("plus", "+")
        expr = expr.replace("minus", "-")
        expr = expr.replace("times", "*")
        expr = expr.replace("multiplied by", "*")
        expr = expr.replace("multiplied", "*")
        expr = expr.replace("divided by", "/")
        expr = expr.replace("divided", "/")
        
        # Safe sanitization: only allow digits, arithmetic symbols, spaces and dots
        sanitized = re.sub(r'[^0-9+\-*/().\s]', '', expr).strip()
        
        if not sanitized:
            return False, "Could not extract a valid mathematical expression to calculate."
            
        try:
            # Safe evaluation in empty namespace
            result = eval(sanitized, {"__builtins__": None}, {})
            # Format float output
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return True, f"The result is {result}."
        except ZeroDivisionError:
            return False, "Division by zero is undefined."
        except Exception:
            return False, f"Could not compute the expression: '{sanitized}'"
