from __future__ import annotations


def summarize_text(text: str, max_points: int = 5) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    points: list[str] = []

    for line in lines:
        sentence = line[:220]
        if sentence not in points:
            points.append(sentence)
        if len(points) >= max_points:
            break

    if not points:
        return ["No significant content found."]
    return points
