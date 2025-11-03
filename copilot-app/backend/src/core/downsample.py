# src/core/downsample.py
"""
Largest Triangle Three Buckets (LTTB) downsampling algorithm
For efficient visualization of large time series
"""
from typing import List, Tuple

def lttb(points: List[Tuple[float, float]], threshold: int = 1000) -> List[Tuple[float, float]]:
    """
    Downsample points using LTTB algorithm.
    
    Args:
        points: List of (x, y) tuples
        threshold: Target number of points
        
    Returns:
        Downsampled list of (x, y) tuples
    """
    if len(points) <= threshold or threshold < 3:
        return points
    
    # Always keep first and last
    sampled = [points[0]]
    bucket_size = (len(points) - 2) / (threshold - 2)
    
    a = 0
    next_a = 0
    
    for i in range(threshold - 2):
        # Calculate bucket
        avg_range_start = int((i + 1) * bucket_size) + 1
        avg_range_end = int((i + 2) * bucket_size) + 1
        
        if avg_range_end >= len(points):
            avg_range_end = len(points)
        
        avg_range_length = avg_range_end - avg_range_start
        
        # Calculate average of next bucket
        avg_x = 0.0
        avg_y = 0.0
        
        for j in range(avg_range_start, avg_range_end):
            avg_x += points[j][0]
            avg_y += points[j][1]
        
        avg_x /= avg_range_length
        avg_y /= avg_range_length
        
        # Get the range for this bucket
        range_offs = int(i * bucket_size) + 1
        range_to = int((i + 1) * bucket_size) + 1
        
        # Point a
        point_a_x = points[a][0]
        point_a_y = points[a][1]
        
        max_area = -1.0
        
        for j in range(range_offs, range_to):
            # Calculate triangle area
            area = abs(
                (point_a_x - avg_x) * (points[j][1] - point_a_y) -
                (point_a_x - points[j][0]) * (avg_y - point_a_y)
            ) * 0.5
            
            if area > max_area:
                max_area = area
                next_a = j
        
        sampled.append(points[next_a])
        a = next_a
    
    sampled.append(points[-1])
    
    return sampled
