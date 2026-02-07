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
    
    use_random_num_dots: bool = Field(
        default=True,
        description="Whether to randomly vary the number of dots for each task"
    )
    
    min_dots: int = Field(
        default=4,
        ge=3,
        le=15,
        description="Minimum number of dots when using random (inclusive)"
    )
    
    max_dots: int = Field(
        default=8,
        ge=3,
        le=15,
        description="Maximum number of dots when using random (inclusive)"
    )
    
    num_dots: int = Field(
        default=5,
        ge=3,
        le=15,
        description="Fixed number of dots (used when use_random_num_dots=False)"
    )
    
    dot_radius: int = Field(
        default=45,
        ge=5,
        le=60,
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
    
    use_multiple_dot_colors: bool = Field(
        default=True,
        description="Whether to use multiple colors for dots (random per dot)"
    )
    
    dot_color: tuple[int, int, int] = Field(
        default=(100, 150, 255),
        description="Default color of dots (RGB) - Used when use_multiple_dot_colors=False"
    )
    
    dot_color_palette: list[tuple[int, int, int]] = Field(
        default_factory=lambda: [
            (100, 150, 255),  # Bright blue
            (255, 100, 150),  # Pink
            (150, 255, 100),  # Bright green
            (255, 200, 100),  # Orange
            (200, 100, 255),  # Purple
            (100, 255, 255),  # Cyan
            (255, 255, 100),  # Yellow
            (255, 150, 100),  # Coral
        ],
        description="Color palette for dots when using multiple colors"
    )
    
    line_color: tuple[int, int, int] = Field(
        default=(255, 80, 80),
        description="Color of connecting lines (RGB) - Bright red for high contrast"
    )
    
    number_color: tuple[int, int, int] = Field(
        default=(255, 255, 255),
        description="Color of numbers on dots (RGB) - White for maximum contrast"
    )
    
    background_color: tuple[int, int, int] = Field(
        default=(255, 255, 255),
        description="Background color (RGB)"
    )
