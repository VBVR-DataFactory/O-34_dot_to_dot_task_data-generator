"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                           YOUR TASK CONFIGURATION                             ║
║                                                                               ║
║  CUSTOMIZE THIS FILE to define your task-specific settings.                   ║
║  Inherits common settings from core.GenerationConfig                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from pydantic import Field
from core import GenerationConfig


class TaskConfig(GenerationConfig):
    """
    Your task-specific configuration.
    
    CUSTOMIZE THIS CLASS to add your task's hyperparameters.
    
    Inherited from GenerationConfig:
        - num_samples: int          # Number of samples to generate
        - domain: str               # Task domain name
        - difficulty: Optional[str] # Difficulty level
        - random_seed: Optional[int] # For reproducibility
        - output_dir: Path          # Where to save outputs
        - image_size: tuple[int, int] # Image dimensions
    """
    
    # ══════════════════════════════════════════════════════════════════════════
    #  OVERRIDE DEFAULTS
    # ══════════════════════════════════════════════════════════════════════════
    
    domain: str = Field(default="dot_to_dot")
    image_size: tuple[int, int] = Field(default=(1024, 1024))
    
    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    
    generate_videos: bool = Field(
        default=True,
        description="Whether to generate ground truth videos"
    )
    
    video_fps: int = Field(
        default=16,
        description="Video frame rate"
    )
    
    # ══════════════════════════════════════════════════════════════════════════
    #  DOT-TO-DOT TASK SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    
    num_dots: int = Field(
        default=5,
        ge=3,
        le=15,
        description="Number of dots in the puzzle"
    )
    
    dot_radius: int = Field(
        default=28,
        ge=5,
        le=30,
        description="Radius of each dot in pixels"
    )
    
    line_width: int = Field(
        default=5,
        ge=2,
        le=5,
        description="Width of connecting lines"
    )
    
    show_numbers: bool = Field(
        default=True,
        description="Whether to show numbers on dots indicating connection order"
    )
    
    connection_type: str = Field(
        default="sequential",
        description="Connection type: 'sequential' (1-2-3-...), 'path' (shortest path), 'random'"
    )
    
    dot_color: tuple[int, int, int] = Field(
        default=(50, 50, 200),
        description="Color of dots (RGB)"
    )
    
    line_color: tuple[int, int, int] = Field(
        default=(200, 50, 50),
        description="Color of connecting lines (RGB)"
    )
    
    background_color: tuple[int, int, int] = Field(
        default=(255, 255, 255),
        description="Background color (RGB)"
    )
