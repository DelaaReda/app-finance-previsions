# src/core/downsample.py
from __future__ import annotations
from typing import List, Tuple

def lttb(points: List[Tuple[float, float]], threshold: int = 1000) -> List[Tuple[float, float]]:
    """
    Largest-Triangle-Three-Buckets downsampling.
    points: [(x,y)] triés par x (x = timestamp en secondes par ex.)
    """
    if threshold >= len(points) or threshold == 0:
        return points

    sampled = [points[0]]
    every = (len(points) - 2) / (threshold - 2)
    a = 0
    for i in range(0, threshold - 2):
        avg_range_start = int((i + 1) * every) + 1
        avg_range_end = int((i + 2) * every) + 1
        if avg_range_end >= len(points):
            avg_range_end = len(points)
        avg_x = sum(p[0] for p in points[avg_range_start:avg_range_end]) / max(1, (avg_range_end - avg_range_start))
        avg_y = sum(p[1] for p in points[avg_range_start:avg_range_end]) / max(1, (avg_range_end - avg_range_start))

        range_offs = int(i * every) + 1
        range_to = int((i + 1) * every) + 1

        ax, ay = points[a]
        max_area = -1.0
        next_a = None
        for j in range(range_offs, range_to):
            area = abs((ax - avg_x) * (points[j][1] - ay) - (ax - points[j][0]) * (avg_y - ay)) * 0.5
            if area > max_area:
                max_area = area
                next_a = j
        sampled.append(points[next_a])
        a = next_a
    sampled.append(points[-1])
    return sampled