
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4, UUID


class SpeakerSegment(BaseModel):
    """Speaker segment: represents a segment of speech by a single speaker """
    start: float = None
    end: float = None
    speaker: str = None
    text: str = None

    def duration(self):
        return self.end - self.start

    def __str__(self):
        return f"Speaker: {self.speaker} | Duration: {self.duration()} | Text: {self.text}"


class TSegment(BaseModel):
    """Transcription segments: represents a segment of speech as decoded by the ASR model"""
    start: Optional[float] = None
    end: Optional[float] = None
    speaker_segments: List[SpeakerSegment] = []
    ttd_model_ms : Optional[float] = None # time taken by the model to decode the segment
    ttd_rt_ms : Optional[float] = None # time taken by the model + API call to decode the segment

    def duration(self):
        return self.speaker_segments[-1].end - self.speaker_segments[0].start

    def compact(self):
        merged_segments = []
        current_segment = SpeakerSegment()

        for segment in self.speaker_segments:

            if segment.speaker == current_segment.speaker:
                current_segment.text += segment.text
                current_segment.end = segment.end
            else:
                if current_segment.speaker is not None:
                    merged_segments.append(current_segment)

                current_segment = SpeakerSegment()
                current_segment.speaker = segment.speaker
                current_segment.text = segment.text
                current_segment.start = segment.start
                current_segment.end = segment.end

        if current_segment.speaker is not None:
            merged_segments.append(current_segment)

        self.speaker_segments = merged_segments

    def __str__(self):
        return "".join([ f"[{segment.speaker}]:{segment.text}\n" for segment in self.speaker_segments])


class Transcription(BaseModel):
    """Transcription: represents the concatenated output of the ASR model"""
    model: str
    metadata: dict = {} # metadata to identify the run
    segments: List[TSegment]
    ttd_user_ms : float = None # time taken by the model + API call to decode | set by user

    def ttd_model_calc_ms(self):
        return sum([segment.ttd_model_ms for segment in self.segments])

    def ttd_rt_calc_ms(self):
        return sum([segment.ttd_rt_ms for segment in self.segments])
    
