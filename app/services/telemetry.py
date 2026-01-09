#!/usr/bin/env python3
"""Telemetry Service - System Metrics for FBP Backend

Optimized for: iMac M3 (Mac15,5) | 8 cores (4P+4E) | 16GB RAM | macOS 26.0 Tahoe
Monitors system resources during NFA batch processing.
"""

from datetime import datetime
from typing import Any, Dict

import psutil

from app.core.config import HARDWARE_PROFILE, M3_LIMITS


def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics with M3-specific info."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # Memory metrics
        memory = psutil.virtual_memory()

        # Disk metrics
        disk = psutil.disk_usage('/')

        # Network metrics
        net_io = psutil.net_io_counters()

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "hardware": {
                "model": HARDWARE_PROFILE["model"],
                "chip": HARDWARE_PROFILE["chip"],
                "cores": f"{HARDWARE_PROFILE['performance_cores']}P+{HARDWARE_PROFILE['efficiency_cores']}E",
                "neural_engine_tops": HARDWARE_PROFILE["neural_engine_tops"],
            },
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else 0
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_system_health() -> Dict[str, Any]:
    """Check if system can handle more browser instances.
    
    Optimized for M3 with 16GB unified memory.
    """
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)

    # M3-specific thresholds
    memory_threshold = M3_LIMITS["safe_memory_threshold"] * 100  # 80%

    return {
        "healthy": mem.percent < memory_threshold and cpu < 90,
        "memory_percent": mem.percent,
        "cpu_percent": cpu,
        "memory_available_gb": round(mem.available / (1024**3), 2),
        "can_spawn_browser": mem.available > M3_LIMITS["browser_memory_mb"] * 1024 * 1024,
        "m3_optimized": True,
    }


def should_pause_batch() -> bool:
    """Returns True if system is under stress - use to throttle NFA batches.
    
    M3-aware: respects 80% memory threshold for unified memory architecture.
    """
    health = check_system_health()
    return not health["healthy"]


def get_browser_recommendation() -> Dict[str, Any]:
    """Recommend max concurrent browser instances based on M3 capabilities.
    
    M3 with 16GB unified memory:
    - Each Playwright browser uses ~1.5GB
    - Max 3 concurrent browsers (leaves ~7GB for system + app)
    - Neural Engine (18 TOPS) available for AI inference
    """
    mem = psutil.virtual_memory()
    available_gb = mem.available / (1024**3)

    # M3-specific: Calculate based on known browser memory usage
    browser_memory_gb = M3_LIMITS["browser_memory_mb"] / 1024
    calculated_max = int(available_gb / browser_memory_gb)

    # Cap at M3 limit (3 browsers max for stability)
    recommended = min(calculated_max, M3_LIMITS["max_concurrent_browsers"])
    recommended = max(1, recommended)  # At least 1

    return {
        "available_memory_gb": round(available_gb, 2),
        "recommended_max_browsers": recommended,
        "m3_max_limit": M3_LIMITS["max_concurrent_browsers"],
        "warning": available_gb < 3,
        "optimal_batch_size": M3_LIMITS["batch_size_default"],
        "hardware": HARDWARE_PROFILE["model"],
    }


# Quick test
if __name__ == "__main__":
    import json
    print("=== System Metrics ===")
    print(json.dumps(get_system_metrics(), indent=2))
    print("\n=== Health Check ===")
    print(json.dumps(check_system_health(), indent=2))
    print("\n=== Browser Recommendation ===")
    print(json.dumps(get_browser_recommendation(), indent=2))
