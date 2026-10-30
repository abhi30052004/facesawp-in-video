import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from app.services.face_detector import DetectedFace

logger = logging.getLogger("bollyswap.services.tracker")


def calculate_iou(box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
    """
    Computes Intersection over Union (IoU) between two bounding boxes [x, y, w, h].
    """
    xa1, ya1, wa, ha = box_a
    xa2, ya2 = xa1 + wa, ya1 + ha

    xb1, yb1, wb, hb = box_b
    xb2, yb2 = xb1 + wb, yb1 + hb

    inter_x1 = max(xa1, xb1)
    inter_y1 = max(ya1, yb1)
    inter_x2 = min(xa2, xb2)
    inter_y2 = min(ya2, yb2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = wa * ha
    area_b = wb * hb
    union_area = area_a + area_b - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / float(union_area)


@dataclass
class FaceTrackHypothesis:
    """A cluster of continuous detections representing a candidate actor track."""
    track_id: str
    label: str
    detections: List[DetectedFace]

    @property
    def occurrences(self) -> int:
        return len(self.detections)

    @property
    def timestamps(self) -> List[float]:
        return [d.timestamp_seconds for d in self.detections]

    @property
    def average_confidence(self) -> float:
        if not self.detections:
            return 0.0
        return round(sum(d.confidence for d in self.detections) / len(self.detections), 4)

    @property
    def representative_detection(self) -> DetectedFace:
        """Selects the detection with the highest confidence and clear resolution."""
        return max(
            self.detections,
            key=lambda d: (d.confidence, d.bbox[2] * d.bbox[3]),
        )


class FaceTracker:
    """
    Groups YuNet face detections across sampled video frames into candidate actor tracks.
    Uses spatial IoU overlap and temporal proximity.
    Maintains transparency: tracks represent tracking hypotheses, not verified identities.
    """

    def __init__(
        self,
        iou_threshold: float = 0.25,
        max_time_gap_seconds: float = 3.5,
    ):
        self.iou_threshold = iou_threshold
        self.max_time_gap_seconds = max_time_gap_seconds

    def cluster_tracks(self, detections: List[DetectedFace]) -> List[FaceTrackHypothesis]:
        """
        Groups chronological face detections into candidate continuous tracks.
        """
        if not detections:
            return []

        # Sort detections chronologically
        sorted_detections = sorted(detections, key=lambda d: (d.timestamp_seconds, d.frame_index))

        # Active tracks under construction: list of FaceTrackHypothesis
        tracks: List[FaceTrackHypothesis] = []
        track_counter = 1

        for det in sorted_detections:
            best_match: Optional[FaceTrackHypothesis] = None
            best_iou = 0.0

            # Match against existing tracks
            for track in tracks:
                last_det = track.detections[-1]
                time_gap = det.timestamp_seconds - last_det.timestamp_seconds

                # Must be forward in time and within allowed temporal gap (avoids matching after huge scene cuts)
                if 0.0 <= time_gap <= self.max_time_gap_seconds:
                    iou = calculate_iou(det.bbox, last_det.bbox)
                    if iou >= self.iou_threshold and iou > best_iou:
                        best_iou = iou
                        best_match = track

            if best_match is not None:
                best_match.detections.append(det)
            else:
                # Start new track hypothesis
                new_track = FaceTrackHypothesis(
                    track_id=f"track_{track_counter}",
                    label=f"Actor #{track_counter}",
                    detections=[det],
                )
                tracks.append(new_track)
                track_counter += 1

        # Sort tracks by prominence: most appearances and highest confidence
        tracks.sort(key=lambda t: (t.occurrences, t.average_confidence), reverse=True)

        # Relabel tracks cleanly based on sorted priority: "Actor #1 (Lead)", "Actor #2", etc.
        for idx, track in enumerate(tracks):
            track_num = idx + 1
            track.track_id = f"track_{track_num}"
            if track_num == 1 and track.occurrences > 1:
                track.label = f"Actor #{track_num} (Principal Subject)"
            else:
                track.label = f"Actor #{track_num}"

        logger.info("Formed %d track hypotheses from %d detections", len(tracks), len(detections))
        return tracks

