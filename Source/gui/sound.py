"""Âm thanh: hiệu ứng ngắn (QSoundEffect) + nhạc nền tùy chọn (QMediaPlayer). (Scope F)

Thiếu file hoặc thiếu QtMultimedia thì im lặng, không làm hỏng game.
File: gui/assets/sounds/<tên>.wav (sinh tạm bằng tools/make_sounds.py).
Nhạc nền (.ogg/.mp3/.wav, tùy chọn): bgm.* cho menu bản đồ, level_01.* ... level_09.* cho 9 màn
(play_music("menu") / play_music("level_03")). Màn nào thiếu file thì dùng nhạc menu.
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
        self._music_path: Optional[Path] = None
        self._after_fade = None
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
        self._audio = QAudioOutput(self)
        self._audio.setVolume(0.0)                 # fade-in từ 0
        self._music = QMediaPlayer(self)
        self._music.setAudioOutput(self._audio)
        self._music.setLoops(QMediaPlayer.Loops.Infinite)
        self._fade = QPropertyAnimation(self._audio, b"volume", self)
        self._fade.finished.connect(self._on_fade_done)

    @staticmethod
    def _track_path(key: str) -> Optional[Path]:
        """File nhạc của `key` ("menu" -> bgm.*, "level_03" -> level_03.*); thiếu thì dùng nhạc menu."""
        for stem in (("bgm",) if key == "menu" else (key, "bgm")):
            for ext in ("ogg", "mp3", "wav"):     # ưu tiên OGG: loop không bị khoảng lặng như MP3
                path = SOUND_DIR / f"{stem}.{ext}"
                if path.exists():
                    return path
        return None

    def _ramp(self, end: float, ms: int, done=None) -> None:
        self._fade.stop()
        self._after_fade = done
        self._fade.setDuration(ms)
        self._fade.setStartValue(self._audio.volume())
        self._fade.setEndValue(end)
        self._fade.start()

    def _on_fade_done(self) -> None:
        callback, self._after_fade = self._after_fade, None
        if callback:
            callback()

    def _load_music(self) -> None:
        """Nạp bài đang chọn và vào nhạc dần (sau khi bài cũ đã nhỏ dần về 0)."""
        self._music.stop()
        if self._music_path is None:
            return
        self._music.setSource(QUrl.fromLocalFile(str(self._music_path)))
        if self.enabled and self._music_wanted:
            self._audio.setVolume(0.0)
            self._music.play()
            self._ramp(MUSIC_VOLUME, 1500)
        else:
            self._audio.setVolume(MUSIC_VOLUME)

    def play(self, name: str) -> None:
        pool = self._pools.get(name)
        if not self.enabled or not pool:
            return
        index = self._next[name]
        self._next[name] = (index + 1) % len(pool)
        pool[index].play()

    def play_music(self, key: str = "menu") -> None:
        """Chọn bài nhạc nền theo `key`. Cùng bài đang phát thì giữ nguyên; khác bài thì bài cũ nhỏ dần
        rồi bài mới vào dần."""
        self._music_wanted = True
        if self._music is None:
            return
        path = self._track_path(key)
        playing = self._music.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        if path == self._music_path:
            if path is not None and self.enabled and not playing and self._after_fade is None:
                self._music.play()
                self._ramp(MUSIC_VOLUME, 1500)
            return
        self._music_path = path
        if playing and self.enabled:
            self._ramp(0.0, 500, self._load_music)
        else:
            self._load_music()

    def start_music(self) -> None:
        """Bật nhạc menu (giữ cho code cũ gọi)."""
        self.play_music("menu")

    def stop_music(self) -> None:
        self._music_wanted = False
        if self._music is not None:
            self._fade.stop()
            self._music.stop()
            self._music_path = None

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