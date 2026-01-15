"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      DOT-TO-DOT TASK GENERATOR                                ║
║                                                                               ║
║  Generates dot-to-dot connection tasks for video model evaluation.            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import random
import math
import tempfile
from pathlib import Path
from typing import List, Tuple, Dict
from PIL import Image, ImageDraw, ImageFont

from core import BaseGenerator, TaskPair, ImageRenderer
from core.video_utils import VideoGenerator
from .config import TaskConfig
from .prompts import get_prompt


class TaskGenerator(BaseGenerator):
    """
    Dot-to-dot task generator.
    
    Generates tasks where dots need to be connected in a specific order.
    """
    
    def __init__(self, config: TaskConfig):
        super().__init__(config)
        self.renderer = ImageRenderer(image_size=config.image_size)
        
        # Initialize video generator if enabled
        self.video_generator = None
        if config.generate_videos and VideoGenerator.is_available():
            self.video_generator = VideoGenerator(fps=config.video_fps, output_format="mp4")
    
    def generate_task_pair(self, task_id: str) -> TaskPair:
        """Generate one dot-to-dot task pair."""
        
        # Generate task data (points and connection order)
        task_data = self._generate_task_data()
        
        # Render images
        first_image = self._render_initial_state(task_data)
        final_image = self._render_final_state(task_data)
        
        # Generate video (optional)
        video_path = None
        if self.config.generate_videos and self.video_generator:
            video_path = self._generate_video(first_image, final_image, task_id, task_data)
        
        # Generate prompt with task data
        prompt = get_prompt(task_data=task_data)
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    #  TASK DATA GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_task_data(self) -> dict:
        """Generate random dots and determine connection order."""
        num_dots = self.config.num_dots
        width, height = self.config.image_size
        
        # Generate random points with padding to avoid edges
        margin = max(self.config.dot_radius * 3, 40)
        points = []
        
        for _ in range(num_dots):
            attempts = 0
            while attempts < 100:
                x = random.randint(margin, width - margin)
                y = random.randint(margin, height - margin)
                
                # Check minimum distance from existing points
                too_close = False
                for px, py in points:
                    dist = math.sqrt((x - px)**2 + (y - py)**2)
                    if dist < margin * 1.5:
                        too_close = True
                        break
                
                if not too_close:
                    points.append((x, y))
                    break
                attempts += 1
            
            if attempts >= 100:
                # Fallback: use grid layout if random placement fails
                grid_size = int(math.ceil(math.sqrt(num_dots)))
                idx = len(points)
                row = idx // grid_size
                col = idx % grid_size
                x = margin + (width - 2 * margin) * col / (grid_size - 1) if grid_size > 1 else width // 2
                y = margin + (height - 2 * margin) * row / (grid_size - 1) if grid_size > 1 else height // 2
                points.append((int(x), int(y)))
        
        # Determine connection order based on connection_type
        connection_order = self._determine_connection_order(points)
        
        return {
            "points": points,
            "connection_order": connection_order,
            "connection_type": self.config.connection_type,
            "num_dots": num_dots,
            "dot_color": self.config.dot_color,
            "line_color": self.config.line_color,
            "background_color": self.config.background_color,
        }
    
    def _determine_connection_order(self, points: List[Tuple[int, int]]) -> List[int]:
        """Determine the order in which dots should be connected."""
        num_dots = len(points)
        
        if self.config.connection_type == "sequential":
            # Simple sequential order: 0, 1, 2, 3, ...
            return list(range(num_dots))
        
        elif self.config.connection_type == "path":
            # Find a path that visits all points (approximate TSP)
            return self._find_path_order(points)
        
        elif self.config.connection_type == "random":
            # Random order
            order = list(range(num_dots))
            random.shuffle(order)
            return order
        
        else:
            # Default to sequential
            return list(range(num_dots))
    
    def _find_path_order(self, points: List[Tuple[int, int]]) -> List[int]:
        """Find a reasonable path order using nearest neighbor heuristic."""
        num_dots = len(points)
        if num_dots <= 1:
            return list(range(num_dots))
        
        # Start from a random point
        start_idx = random.randint(0, num_dots - 1)
        visited = {start_idx}
        order = [start_idx]
        current_idx = start_idx
        
        # Greedily choose nearest unvisited point
        while len(visited) < num_dots:
            min_dist = float('inf')
            next_idx = None
            
            for i in range(num_dots):
                if i not in visited:
                    dist = math.sqrt(
                        (points[i][0] - points[current_idx][0])**2 +
                        (points[i][1] - points[current_idx][1])**2
                    )
                    if dist < min_dist:
                        min_dist = dist
                        next_idx = i
            
            if next_idx is not None:
                order.append(next_idx)
                visited.add(next_idx)
                current_idx = next_idx
            else:
                break
        
        return order
    
    # ══════════════════════════════════════════════════════════════════════════
    #  IMAGE RENDERING
    # ══════════════════════════════════════════════════════════════════════════
    
    def _render_initial_state(self, task_data: dict) -> Image.Image:
        """Render initial state with dots only (no connections)."""
        img = Image.new('RGB', self.config.image_size, self.config.background_color)
        draw = ImageDraw.Draw(img)
        
        points = task_data["points"]
        connection_order = task_data["connection_order"]
        
        # Draw dots
        for idx, (x, y) in enumerate(points):
            # Find the number label for this dot
            dot_number = connection_order.index(idx) + 1
            
            # Draw dot circle
            draw.ellipse(
                [x - self.config.dot_radius, y - self.config.dot_radius,
                 x + self.config.dot_radius, y + self.config.dot_radius],
                fill=self.config.dot_color,
                outline=(0, 0, 0),
                width=2
            )
            
            # Draw number label if enabled
            if self.config.show_numbers:
                font = self._get_font(size=max(24, self.config.dot_radius * 3))
                text = str(dot_number)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Center text on dot
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                
                # Draw text with outline for visibility
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((text_x + dx, text_y + dy), text, font=font, fill=(255, 255, 255))
                draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0))
        
        return img
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        """Render final state with dots connected."""
        img = Image.new('RGB', self.config.image_size, self.config.background_color)
        draw = ImageDraw.Draw(img)
        
        points = task_data["points"]
        connection_order = task_data["connection_order"]
        
        # Draw connecting lines first (so dots appear on top)
        for i in range(len(connection_order) - 1):
            idx1 = connection_order[i]
            idx2 = connection_order[i + 1]
            x1, y1 = points[idx1]
            x2, y2 = points[idx2]
            
            draw.line([(x1, y1), (x2, y2)], fill=self.config.line_color, width=self.config.line_width)
        
        # Draw dots on top
        for idx, (x, y) in enumerate(points):
            # Find the number label for this dot
            dot_number = connection_order.index(idx) + 1
            
            # Draw dot circle
            draw.ellipse(
                [x - self.config.dot_radius, y - self.config.dot_radius,
                 x + self.config.dot_radius, y + self.config.dot_radius],
                fill=self.config.dot_color,
                outline=(0, 0, 0),
                width=2
            )
            
            # Draw number label if enabled
            if self.config.show_numbers:
                font = self._get_font(size=max(24, self.config.dot_radius * 3))
                text = str(dot_number)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Center text on dot
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                
                # Draw text with outline for visibility
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((text_x + dx, text_y + dy), text, font=font, fill=(255, 255, 255))
                draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0))
        
        return img
    
    def _get_font(self, size: int = 20) -> ImageFont.FreeTypeFont:
        """Get a font for rendering numbers."""
        try:
            # Try to load a system font
            font_paths = [
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/Library/Fonts/Arial.ttf",
            ]
            
            for font_path in font_paths:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
        except:
            pass
        
        # Fallback to default font
        try:
            return ImageFont.truetype("arial.ttf", size)
        except:
            return ImageFont.load_default()
    
    # ══════════════════════════════════════════════════════════════════════════
    #  VIDEO GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_video(
        self,
        first_image: Image.Image,
        final_image: Image.Image,
        task_id: str,
        task_data: dict
    ) -> str:
        """Generate ground truth video showing dots being connected sequentially."""
        temp_dir = Path(tempfile.gettempdir()) / f"{self.config.domain}_videos"
        temp_dir.mkdir(parents=True, exist_ok=True)
        video_path = temp_dir / f"{task_id}_ground_truth.mp4"
        
        # Create animation frames
        frames = self._create_connection_animation_frames(task_data)
        
        result = self.video_generator.create_video_from_frames(
            frames,
            video_path
        )
        
        return str(result) if result else None
    
    def _create_connection_animation_frames(
        self,
        task_data: dict,
        hold_frames: int = 5,
        transition_frames_per_connection: int = 15
    ) -> List[Image.Image]:
        """
        Create animation frames showing dots being connected sequentially.
        
        Each connection is animated smoothly over multiple frames.
        """
        frames = []
        points = task_data["points"]
        connection_order = task_data["connection_order"]
        
        # Hold initial state
        initial_frame = self._render_initial_state(task_data)
        for _ in range(hold_frames):
            frames.append(initial_frame.copy())
        
        # Animate each connection
        for connection_idx in range(len(connection_order) - 1):
            idx1 = connection_order[connection_idx]
            idx2 = connection_order[connection_idx + 1]
            
            # Create frames for this connection
            connection_frames = self._animate_single_connection(
                task_data,
                connection_idx + 1,  # Number of connections completed so far
                idx1,
                idx2,
                transition_frames_per_connection
            )
            frames.extend(connection_frames)
        
        # Hold final state
        final_frame = self._render_final_state(task_data)
        for _ in range(hold_frames):
            frames.append(final_frame.copy())
        
        return frames
    
    def _animate_single_connection(
        self,
        task_data: dict,
        num_connections_completed: int,
        from_idx: int,
        to_idx: int,
        num_frames: int
    ) -> List[Image.Image]:
        """Animate drawing a single line between two dots."""
        frames = []
        points = task_data["points"]
        connection_order = task_data["connection_order"]
        
        x1, y1 = points[from_idx]
        x2, y2 = points[to_idx]
        
        for i in range(num_frames):
            progress = i / (num_frames - 1) if num_frames > 1 else 1.0
            
            # Create frame
            img = Image.new('RGB', self.config.image_size, self.config.background_color)
            draw = ImageDraw.Draw(img)
            
            # Draw all completed connections
            for conn_idx in range(num_connections_completed):
                if conn_idx < len(connection_order) - 1:
                    cidx1 = connection_order[conn_idx]
                    cidx2 = connection_order[conn_idx + 1]
                    cx1, cy1 = points[cidx1]
                    cx2, cy2 = points[cidx2]
                    draw.line([(cx1, cy1), (cx2, cy2)], fill=self.config.line_color, width=self.config.line_width)
            
            # Draw current connection (partially)
            if progress > 0:
                current_x = x1 + (x2 - x1) * progress
                current_y = y1 + (y2 - y1) * progress
                draw.line([(x1, y1), (current_x, current_y)], fill=self.config.line_color, width=self.config.line_width)
            
            # Draw all dots
            for idx, (x, y) in enumerate(points):
                dot_number = connection_order.index(idx) + 1
                
                draw.ellipse(
                    [x - self.config.dot_radius, y - self.config.dot_radius,
                     x + self.config.dot_radius, y + self.config.dot_radius],
                    fill=self.config.dot_color,
                    outline=(0, 0, 0),
                    width=2
                )
                
                if self.config.show_numbers:
                    font = self._get_font(size=max(16, self.config.dot_radius * 2))
                    text = str(dot_number)
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    text_x = x - text_width // 2
                    text_y = y - text_height // 2
                    
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            draw.text((text_x + dx, text_y + dy), text, font=font, fill=(255, 255, 255))
                    draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0))
            
            frames.append(img)
        
        return frames
