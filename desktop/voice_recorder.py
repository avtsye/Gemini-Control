"""Opt-in microphone recording to a local WAV file using Qt Multimedia.

A local push-to-talk recorder, not an always-listening background service.
No audio is sent to network services by this component.
"""
import io
import uuid
import wave
from pathlib import Path
from PySide6.QtCore import QObject,QTimer
from PySide6.QtMultimedia import QAudioFormat,QAudioSource,QMediaDevices

class VoiceRecorder(QObject):
    MAX_SECONDS=180
    MAX_BYTES=16000*2*MAX_SECONDS
    def __init__(self,workspace,parent=None):
        super().__init__(parent)
        self.workspace=Path(workspace).expanduser().resolve()
        self.audio=None
        self.device=None
        self.parts=[]
        self.timer=QTimer(self)
        self.timer.timeout.connect(self._read)
        self.recording=False
        self.finished_result=None
    def start(self):
        if self.recording:return {"error":"Recording is already active"}
        microphone=QMediaDevices.defaultAudioInput()
        if microphone.isNull():return {"unavailable":"No microphone available"}
        fmt=QAudioFormat()
        fmt.setSampleRate(16000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not microphone.isFormatSupported(fmt):
            return {"unavailable":"Microphone cannot provide 16 kHz mono PCM16"}
        self.audio=QAudioSource(microphone,fmt,self)
        self.device=self.audio.start()
        if self.device is None:
            self.audio=None
            return {"error":"Cannot start microphone capture"}
        self.parts=[]
        self.finished_result=None
        self.recording=True
        self.timer.start(100)
        return {"recording":True,"sample_rate":16000,"format":"pcm16_mono"}
    def _read(self):
        if not self.recording or self.device is None:return
        data=bytes(self.device.readAll())
        if data:self.parts.append(data)
        if sum(map(len,self.parts))>=self.MAX_BYTES:
            self.finished_result=self.stop()
    def stop(self):
        if not self.recording:
            if self.finished_result is not None:
                result=self.finished_result
                self.finished_result=None
                return result
            return {"error":"No recording in progress"}
        self.timer.stop()
        if self.device is not None:
            final=bytes(self.device.readAll())
            if final:self.parts.append(final)
        self.recording=False
        self.audio.stop()
        data=b"".join(self.parts)[:self.MAX_BYTES]
        self.parts=[]
        self.device=None
        self.audio=None
        if not data:return {"error":"Microphone did not return samples"}
        folder=self.workspace/"recordings"
        folder.mkdir(parents=True,exist_ok=True)
        path=folder/("voice-"+uuid.uuid4().hex+".wav")
        with path.open("xb") as handle:
            with wave.open(handle,"wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(data)
        return {"recorded_file":str(path.relative_to(self.workspace)),
                "seconds":round(len(data)/32000,2),"bytes":len(data)}
