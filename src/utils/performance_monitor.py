from typing import Dict, List, Optional
from datetime import datetime
import statistics

class PerformanceMonitor:
    """Monitors and tracks system performance metrics."""

    def __init__(self):
        self.metrics = {
            "api_requests": 0,
            "classifications": 0,
            "successful_classifications": 0,
            "rule_based_fallbacks": 0,
            "average_confidence": 0,
            "average_processing_time": 0,
            "error_count": 0,
            "error_rate": 0
        }
        self.classifier_metrics = {
            "accuracy": 0,
            "precision": {},
            "recall": {},
            "f1_score": {}
        }

        # Store recent processing times for percentile calculations
        self.recent_processing_times = []
        self.max_recent_samples = 1000  # Keep last 1000 samples

    async def track_request(self, request_type: str, start_time: float,
                      end_time: float, success: bool,
                      details: Dict = None) -> None:
        """
        Track API request performance.

        Args:
            request_type: Type of request (e.g., "classification")
            start_time: Request start timestamp
            end_time: Request end timestamp
            success: Whether request was successful
            details: Additional request details
        """
        processing_time = end_time - start_time

        # Add to recent processing times
        self.recent_processing_times.append(processing_time)
        if len(self.recent_processing_times) > self.max_recent_samples:
            self.recent_processing_times.pop(0)

        # Update metrics
        self.metrics["api_requests"] += 1

        if request_type == "classification":
            self.metrics["classifications"] += 1
            if success:
                self.metrics["successful_classifications"] += 1

                if details and "confidence" in details:
                    # Update running average for confidence
                    current_avg = self.metrics["average_confidence"]
                    current_count = self.metrics["successful_classifications"]
                    self.metrics["average_confidence"] = (
                        (current_avg * (current_count - 1) + details["confidence"]) / current_count
                    )

                if details and "rule_based_fallback" in details and details["rule_based_fallback"]:
                    self.metrics["rule_based_fallbacks"] += 1

        if not success:
            self.metrics["error_count"] += 1

        # Update running average for processing time
        current_avg = self.metrics["average_processing_time"]
        current_count = self.metrics["api_requests"]
        self.metrics["average_processing_time"] = (
            (current_avg * (current_count - 1) + processing_time) / current_count
        )

        # Calculate error rate
        self.metrics["error_rate"] = self.metrics["error_count"] / self.metrics["api_requests"]

    async def update_classifier_metrics(self, metrics: Dict) -> None:
        """Update classifier performance metrics."""
        self.classifier_metrics.update(metrics)

    async def get_performance_report(self) -> Dict:
        """Generate a performance report."""
        # Calculate percentiles for processing time
        processing_times = self._calculate_processing_time_percentiles()

        return {
            "api_metrics": {
                **self.metrics,
                "processing_times": processing_times
            },
            "classifier_metrics": self.classifier_metrics,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_processing_time_percentiles(self) -> Dict:
        """Calculate percentiles for processing times."""
        if not self.recent_processing_times:
            return {
                "min": 0,
                "p50": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0,
                "max": 0
            }

        sorted_times = sorted(self.recent_processing_times)
        n = len(sorted_times)

        return {
            "min": sorted_times[0],
            "p50": sorted_times[n // 2],
            "p90": sorted_times[int(n * 0.9)],
            "p95": sorted_times[int(n * 0.95)],
            "p99": sorted_times[int(n * 0.99)],
            "max": sorted_times[-1]
        }
