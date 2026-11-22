"""Âm thanh: hiệu ứng ngắn (QSoundEffect) + nhạc nền tùy chọn (QMediaPlayer). (Scope F)

Thiếu file hoặc thiếu QtMultimedia thì im lặng, không làm hỏng game.
File: gui/assets/sounds/<tên>.wav (sinh tạm bằng tools/make_sounds.py) và bgm.mp3/.ogg/.wav (tùy chọn).
"""
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject, QPropertyAnimation, QUrl

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QSoundEffect
    HAS_AUDIO = True
except ImportError:                      # thiếu module hoặc backend âm thanh
    HAS_AUDIO = False

SOUND_DIR = Path(__file__).resolve().parent / "assets" / "sounds"
SFX_NAMES = ("click", "radial", "flip", "correct", "not_provable", "thunder",
             "hint", "step", "clue", "victory")
SFX_VOLUME = 0.7
MUSIC_VOLUME = 0.3
POOL_SIZE = 2                            # cho phép cùng một âm chồng lên nhau


class SoundManager(QObject):
    """Phát hiệu ứng theo tên: sound.play("correct"). An toàn khi thiếu file."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.enabled = True
        self._pools: Dict[str, List["QSoundEffect"]] = {}
        self._next: Dict[str, int] = {}
        self._music: Optional["QMediaPlayer"] = None
        self._audio: Optional["QAudioOutput"] = None
        self._music_wanted = False
        self._fade: Optional[QPropertyAnimation] = None
        if not HAS_AUDIO:
            return
        for name in SFX_NAMES:
            path = SOUND_DIR / f"{name}.wav"
            if not path.exists():
                continue
            pool = []
            for _ in range(POOL_SIZE):
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(SFX_VOLUME)
                pool.append(effect)
            self._pools[name], self._next[name] = pool, 0
        self._setup_music()

    def _setup_music(self) -> None:
        # Ưu tiên OGG: loop không bị khoảng lặng như MP3
        for ext in ("ogg", "mp3", "wav"):
            path = SOUND_DIR / f"bgm.{ext}"
            if not path.exists():
                continue
            self._audio = QAudioOutput(self)
            self._audio.setVolume(0.0)             # fade-in từ 0
            self._music = QMediaPlayer(self)
            self._music.setAudioOutput(self._audio)
            self._music.setSource(QUrl.fromLocalFile(str(path)))
            self._music.setLoops(QMediaPlayer.Loops.Infinite)
            self._fade = QPropertyAnimation(self._audio, b"volume", self)
            self._fade.setDuration(1500)           # 1.5 s fade-in
            self._fade.setStartValue(0.0)
            self._fade.setEndValue(MUSIC_VOLUME)
            return

    def play(self, name: str) -> None:
        pool = self._pools.get(name)
        if not self.enabled or not pool:
            return
        index = self._next[name]
        self._next[name] = (index + 1) % len(pool)
        pool[index].play()

    def start_music(self) -> None:
        """Bật BGM (idempotent). Gọi trong _after_reset để nhạc khớp vụ án."""
        self._music_wanted = True
        if self._music is None or not self.enabled:
            return
        if self._music.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return                                      # đang phát rồi
        self._music.play()
        if self._fade is not None:
            self._fade.stop()
            self._fade.start()

    def stop_music(self) -> None:
        self._music_wanted = False
        if self._music is not None:
            self._music.stop()

    def set_music_volume(self, volume: float) -> None:
        if self._audio is not None:
            self._audio.setVolume(max(0.0, min(1.0, volume)))

    def set_sfx_volume(self, volume: float) -> None:
        vol = max(0.0, min(1.0, volume))
        for pool in self._pools.values():
            for effect in pool:
                effect.setVolume(vol)

    def toggle(self) -> bool:
        """Bật/tắt toàn bộ âm thanh; trả về trạng thái mới (True = đang bật)."""
        self.enabled = not self.enabled
        if self._music is not None:
            if self.enabled and self._music_wanted:
                self._music.play()
            else:
                self._music.pause()
        return self.enabled