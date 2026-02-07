"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           DOT-TO-DOT TASK PROMPTS                             ║
║                                                                               ║
║  Simple and clear prompts for dot-to-dot connection tasks.                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


def get_prompt(task_data: dict = None, task_type: str = "default") -> str:
    """
    Generate a simple and clear prompt for the dot-to-dot task.
    
    Args:
        task_data: Dictionary containing task information (num_dots, etc.)
        task_type: Type of task (kept for backward compatibility)
        
    Returns:
        Simple prompt string
    """
    if task_data is None:
        task_data = {}
    
    num_dots = task_data.get("num_dots", 5)
    
    # Simple and clear prompt with step-by-step instruction
    prompt = (
        f"The scene shows {num_dots} numbered dots scattered across the image. "
        f"Connect the dots in numerical order (1→2→3→...→{num_dots}) by drawing red straight lines between them, "
        f"one line at a time in sequence."
    )
    
    return prompt


def get_all_prompts(task_type: str = "default") -> list[str]:
    """Get all prompts for a given task type (for backward compatibility)."""
    return [get_prompt(task_type=task_type)]
