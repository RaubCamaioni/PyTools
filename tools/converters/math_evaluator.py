# math, calculator, expression, evaluate

import ast
import math
import operator

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
FUNCTIONS = {
    name: getattr(math, name)
    for name in (
        "sqrt",
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "atan2",
        "log",
        "log10",
        "log2",
        "exp",
        "floor",
        "ceil",
        "fabs",
        "factorial",
        "gcd",
        "degrees",
        "radians",
        "hypot",
    )
}
FUNCTIONS.update({"abs": abs, "round": round, "min": min, "max": max, "ln": math.log})
CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf}


def math_evaluator(expression: str = "sqrt(3**2 + 4**2) * (1 + 2) / 3") -> dict:
    """Evaluate a maths expression safely: + - * / // % **, parentheses, sqrt, trig
    (radians), log, ln, exp, factorial, gcd, round, min, max, and the constants pi, e
    and tau.
    """
    text = expression.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    try:
        tree = ast.parse(text, mode="eval")
        value = _eval(tree.body)
    except ZeroDivisionError:
        return {"error": "Division by zero"}
    except (ValueError, TypeError, SyntaxError, KeyError, OverflowError, RecursionError) as e:
        return {"error": f"Cannot evaluate: {e}"}
    result = {"expression": text, "result": value}
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        result["result"] = int(value)
    if isinstance(result["result"], int):
        result.update({"hex": hex(result["result"]), "binary": bin(result["result"])})
    elif isinstance(value, float):
        result.update({"rounded_2": round(value, 2), "scientific": f"{value:.6e}"})
    return result


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Name) and node.id in CONSTANTS:
        return CONSTANTS[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10000:
            raise ValueError("exponent too large")
        return OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:
        args = [_eval(a) for a in node.args]
        if node.func.id == "factorial" and args and args[0] > 5000:
            raise ValueError("factorial too large")
        return FUNCTIONS[node.func.id](*args)
    raise ValueError(f"unsupported syntax: {ast.dump(node)[:40]}")
