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
from typing import List, Tuple, Dict, Any
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
        
        # Build objects metadata
        objects = self._build_objects_metadata(task_data)
        
        # Build task_data with object-centric metadata
        optimized_task_data = {
            "num_dots": task_data["num_dots"],
            "connection_type": task_data["connection_type"],
            "line_color": list(task_data["line_color"]),
            "objects": objects
        }
        
        # Build metadata
        metadata = self._build_metadata(task_id, optimized_task_data)
        
        
        
        return TaskPair(
            task_id=task_id,
            domain=self.config.domain,
            prompt=prompt,
            first_image=first_image,
            final_image=final_image,
            ground_truth_video=video_path,
            metadata=metadata
        )
    
    # ══════════════════════════════════════════════════════════════════════════
    #  METADATA BUILDING
    # ══════════════════════════════════════════════════════════════════════════

    def _build_objects_metadata(self, task_data: dict) -> List[Dict[str, Any]]:
        """
        Build objects metadata with all dots as individual objects.
        
        Args:
            task_data: Task data dictionary containing dots information
        
        Returns:
            List of objects with their properties
        """
        objects = []
        points = task_data["points"]
        connection_order = task_data["connection_order"]
        dot_colors = task_data["dot_colors"]
        
        for idx, (x, y) in enumerate(points):
            # Find the number label for this dot (1-indexed)
            position_in_order = connection_order.index(idx)
            dot_number = position_in_order + 1
            
            # Find the next dot index in connection order (if not the last)
            next_dot_index = None
            if position_in_order < len(connection_order) - 1:
                next_dot_index = connection_order[position_in_order + 1]  # Next dot in connection order
            
            objects.append({
                "symbol": "dot",
                "index": idx,  # 0-indexed position in points list
                "number": dot_number,  # 1-indexed number in connection order
                "center": [x, y],
                "color": list(dot_colors[idx]),
                "radius": self.config.dot_radius,
                "next_dot_index": next_dot_index  # Index of next dot to connect to, or None if last
            })
        
        return objects

    # ══════════════════════════════════════════════════════════════════════════
    #  TASK DATA GENERATION
    # ══════════════════════════════════════════════════════════════════════════
    
    def _generate_task_data(self) -> dict:
        """Generate random dots and determine connection order."""
        # Determine number of dots
        if self.config.use_random_num_dots:
            num_dots = random.randint(self.config.min_dots, self.config.max_dots)
        else:
            num_dots = self.config.num_dots

        width, height = self.config.image_size
        margin = max(self.config.dot_radius * 3, 40)

        for _attempt in range(400):
            points = []
            for _ in range(num_dots):
                pt_attempts = 0
                while pt_attempts < 100:
                    x = random.randint(margin, width - margin)
                    y = random.randint(margin, height - margin)
                    too_close = False
                    for px, py in points:
                        dist = math.sqrt((x - px) ** 2 + (y - py) ** 2)
                        if dist < margin * 1.5:
                            too_close = True
                            break
                    if not too_close:
                        points.append((x, y))
                        break
                    pt_attempts += 1
                if pt_attempts >= 100:
                    grid_size = int(math.ceil(math.sqrt(num_dots)))
                    idx = len(points)
                    row = idx // grid_size
                    col = idx % grid_size
                    x = margin + (width - 2 * margin) * col / (grid_size - 1) if grid_size > 1 else width // 2
                    y = margin + (height - 2 * margin) * row / (grid_size - 1) if grid_size > 1 else height // 2
                    points.append((int(x), int(y)))

            connection_order = self._determine_connection_order(points)
            if self._connection_polylines_respect_other_dots(points, connection_order):
                dot_colors = self._assign_dot_colors(num_dots)
                return {
                    "points": points,
                    "connection_order": connection_order,
                    "connection_type": self.config.connection_type,
                    "num_dots": num_dots,
                    "dot_colors": dot_colors,
                    "line_color": self.config.line_color,
                    "background_color": self.config.background_color,
                }

        raise RuntimeError("Could not sample dot layout with non-crossing segments")

    def _point_segment_distance_sq(
        self,
        px: float,
        py: float,
        ax: float,
        ay: float,
        bx: float,
        by: float,
    ) -> float:
        """Squared distance from point P to segment AB."""
        abx, aby = bx - ax, by - ay
        apx, apy = px - ax, py - ay
        ab_len_sq = abx * abx + aby * aby
        if ab_len_sq < 1e-6:
            return (px - ax) ** 2 + (py - ay) ** 2
        t = max(0.0, min(1.0, (apx * abx + apy * aby) / ab_len_sq))
        cx, cy = ax + t * abx, ay + t * aby
        return (px - cx) ** 2 + (py - cy) ** 2

    def _connection_polylines_respect_other_dots(
        self,
        points: List[Tuple[int, int]],
        connection_order: List[int],
    ) -> bool:
        """
        Each segment between consecutive dots in order must not pass too close to
        any other numbered dot (avoids ambiguous 'line through another label').
        """
        r = self.config.dot_radius + self.config.line_width + 6
        r_sq = r * r
        n = len(connection_order)
        for i in range(n - 1):
            a = connection_order[i]
            b = connection_order[i + 1]
            ax, ay = points[a]
            bx, by = points[b]
            for j, (px, py) in enumerate(points):
                if j in (a, b):
                    continue
                if self._point_segment_distance_sq(px, py, ax, ay, bx, by) < r_sq:
                    return False
        return True
    
    def _assign_dot_colors(self, num_dots: int) -> List[Tuple[int, int, int]]:
        """Assign colors to dots based on configuration."""
        if self.config.use_multiple_dot_colors and hasattr(self.config, 'dot_color_palette'):
            # Use color palette - randomly assign colors
            colors = []
            palette = self.config.dot_color_palette
            for _ in range(num_dots):
                colors.append(random.choice(palette))
            return colors
        else:
            # Use single color for all dots
            return [self.config.dot_color] * num_dots
    
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
        dot_colors = task_data["dot_colors"]
        
        # Draw dots
        for idx, (x, y) in enumerate(points):
            # Find the number label for this dot
            dot_number = connection_order.index(idx) + 1
            
            # Get color for this dot
            dot_color = dot_colors[idx]
            
            # Draw dot circle
            draw.ellipse(
                [x - self.config.dot_radius, y - self.config.dot_radius,
                 x + self.config.dot_radius, y + self.config.dot_radius],
                fill=dot_color,
                outline=(0, 0, 0),
                width=3
            )
            
            # Draw number label if enabled
            if self.config.show_numbers:
                # Calculate font size to fit within dot (about 60% of diameter)
                font_size = int(self.config.dot_radius * 1.2)
                font = self._get_font(size=font_size)
                text = str(dot_number)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Center text on dot
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                
                # Get number color from config, default to white
                number_color = getattr(self.config, 'number_color', (255, 255, 255))
                
                # Draw text with slight shadow for better visibility
                draw.text((text_x + 2, text_y + 2), text, font=font, fill=(0, 0, 0))
                draw.text((text_x, text_y), text, font=font, fill=number_color)
        
        return img
    
    def _render_final_state(self, task_data: dict) -> Image.Image:
        """Render final state with dots connected."""
        img = Image.new('RGB', self.config.image_size, self.config.background_color)
        draw = ImageDraw.Draw(img)
        
        points = task_data["points"]
        connection_order = task_data["connection_order"]
        dot_colors = task_data["dot_colors"]
        
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
            
            # Get color for this dot
            dot_color = dot_colors[idx]
            
            # Draw dot circle
            draw.ellipse(
                [x - self.config.dot_radius, y - self.config.dot_radius,
                 x + self.config.dot_radius, y + self.config.dot_radius],
                fill=dot_color,
                outline=(0, 0, 0),
                width=3
            )
            
            # Draw number label if enabled
            if self.config.show_numbers:
                # Calculate font size to fit within dot (about 60% of diameter)
                font_size = int(self.config.dot_radius * 1.2)
                font = self._get_font(size=font_size)
                text = str(dot_number)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Center text on dot
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                
                # Get number color from config, default to white
                number_color = getattr(self.config, 'number_color', (255, 255, 255))
                
                # Draw text with slight shadow for better visibility
                draw.text((text_x + 2, text_y + 2), text, font=font, fill=(0, 0, 0))
                draw.text((text_x, text_y), text, font=font, fill=number_color)
        
        return img
    
    def _get_font(self, size: int = 20) -> ImageFont.FreeTypeFont:
        """Get a font for rendering numbers."""
        font_candidates = [
            # Bundled in Docker image - guaranteed to exist in Lambda
            "/opt/fonts/DejaVuSans-Bold.ttf",
            "/opt/fonts/DejaVuSans.ttf",
            # Amazon Linux 2 (Lambda) - RPM convention, no truetype/ subdir
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            # Ubuntu/Debian convention (kept as fallback)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            # macOS
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            # bare name - let Pillow/FreeType search
            "DejaVuSans-Bold.ttf",
            "DejaVuSans.ttf",
            "arial.ttf",
        ]
        for font_path in font_candidates:
            try:
                return ImageFont.truetype(font_path, size)
            except (OSError, IOError):
                continue
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
        dot_colors = task_data["dot_colors"]
        
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
                dot_color = dot_colors[idx]
                
                draw.ellipse(
                    [x - self.config.dot_radius, y - self.config.dot_radius,
                     x + self.config.dot_radius, y + self.config.dot_radius],
                    fill=dot_color,
                    outline=(0, 0, 0),
                    width=3
                )
                
                if self.config.show_numbers:
                    font_size = int(self.config.dot_radius * 1.2)
                    font = self._get_font(size=font_size)
                    text = str(dot_number)
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    text_x = x - text_width // 2
                    text_y = y - text_height // 2
                    
                    number_color = getattr(self.config, 'number_color', (255, 255, 255))
                    draw.text((text_x + 2, text_y + 2), text, font=font, fill=(0, 0, 0))
                    draw.text((text_x, text_y), text, font=font, fill=number_color)
            
            frames.append(img)
        
        return frames
