"""Sinh bộ âm thanh tạm (WAV, tự tổng hợp bằng thư viện chuẩn) cho game. (Scope F)

Chạy từ thư mục Source/:  python tools/make_sounds.py
Ghi vào gui/assets/sounds/. Muốn dùng âm thanh riêng: chép đè file cùng tên (WAV, mono hoặc stereo).
Không dùng nhạc/âm thanh gốc của Conan trong bản nộp công khai vì có bản quyền.
"""
import math
import random
import struct
import wave
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

RATE = 22050
OUT_DIR = Path(__file__).resolve().parent.parent / "gui" / "assets" / "sounds"
Samples = List[float]


def tone(freq: float, dur: float, vol: float = 0.5, decay: float = 6.0,
         harmonics: Sequence[Tuple[int, float]] = ((1, 1.0),)) -> Samples:
    out = []
    for i in range(int(RATE * dur)):
        t = i / RATE
        env = math.exp(-decay * t / dur) * min(1.0, t / 0.004)
        out.append(vol * env * sum(a * math.sin(2 * math.pi * freq * h * t) for h, a in harmonics))
    return out


def sweep(f0: float, f1: float, dur: float, vol: float = 0.4) -> Samples:
    out, phase, n = [], 0.0, int(RATE * dur)
    for i in range(n):
        phase += 2 * math.pi * (f0 + (f1 - f0) * i / n) / RATE
        out.append(vol * math.sin(math.pi * i / n) * math.sin(phase))
    return out


def noise(dur: float, vol: float, decay: float, smooth: float, seed: int = 1) -> Samples:
    """Nhiễu trắng qua bộ lọc thông thấp một cực (smooth nhỏ = trầm hơn)."""
    rng, out, last = random.Random(seed), [], 0.0
    for i in range(int(RATE * dur)):
        last += smooth * (rng.uniform(-1, 1) - last)
        out.append(vol * math.exp(-decay * i / (RATE * dur)) * last)
    return out


def layer(*parts: Tuple[Samples, float]) -> Samples:
    """Chồng các đoạn, mỗi đoạn kèm thời điểm bắt đầu (giây)."""
    length = max(int(off * RATE) + len(s) for s, off in parts)
    out = [0.0] * length
    for samples, offset in parts:
        start = int(offset * RATE)
        for i, v in enumerate(samples):
            out[start + i] += v
    return out


def save(name: str, samples: Samples) -> float:
    peak = max(max(abs(v) for v in samples), 1e-9)
    data = b"".join(struct.pack("<h", int(32767 * 0.85 * v / peak)) for v in samples)
    with wave.open(str(OUT_DIR / f"{name}.wav"), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(data)
    return len(samples) / RATE


def build() -> Dict[str, Samples]:
    bell = ((1, 1.0), (2, 0.3), (3, 0.1))
    notes = {"C5": 523.25, "E5": 659.25, "G5": 783.99, "C6": 1046.5, "E6": 1318.5, "G6": 1568.0}
    return {
        "click": tone(1400, 0.04, 0.5, 9),
        "radial": sweep(250, 900, 0.18, 0.35),
        "flip": layer((noise(0.22, 0.6, 5, 0.35), 0.0), (tone(160, 0.12, 0.5, 8), 0.0)),
        "correct": layer(*[(tone(notes[k], 0.5, 0.4, 5, bell), i * 0.09)
                           for i, k in enumerate(("C6", "E6", "G6"))]),
        "not_provable": layer((tone(220, 0.18, 0.5, 3, ((1, 1.0), (3, 0.3))), 0.0),
                              (tone(165, 0.3, 0.5, 3, ((1, 1.0), (3, 0.3))), 0.17)),
        "thunder": layer((noise(1.4, 0.9, 3, 0.08, 2), 0.0), (noise(0.08, 1.0, 4, 0.6, 3), 0.0),
                         (tone(55, 1.0, 0.6, 3), 0.0)),
        "hint": layer(*[(tone(1760, 0.07, 0.5, 4), i * 0.12) for i in range(3)]),
        "step": tone(880, 0.06, 0.4, 8),
        "clue": sweep(500, 2000, 0.28, 0.35),
        "victory": layer(*[(tone(notes[k], 0.5, 0.4, 3, bell), i * 0.18)
                           for i, k in enumerate(("C5", "E5", "G5", "C6"))],
                         *[(tone(notes[k], 1.2, 0.3, 2.5, bell), 0.8) for k in ("C5", "E5", "G5", "C6")]),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, samples in build().items():
        print(f"{name}.wav  {save(name, samples):.2f}s")


if __name__ == "__main__":
    main()
