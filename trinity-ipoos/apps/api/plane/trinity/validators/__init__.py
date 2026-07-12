"""
Trinity Validation Engine — Deterministic Rule-Based Compliance Checker

Every rule is plain conditional logic — no LLM, no ML, no heuristics.
Each rule function takes structured data and returns a list of FlagResult objects.
The engine runs all rules and persists the results to the database.
"""
