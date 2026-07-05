"""用標準函式庫合成遊戲音效（無外部依賴），輸出到 assets/sfx/*.wav。
執行：.\\venv\\Scripts\\python.exe scripts\\gen_sfx.py
音色調整就改這裡再重生，不要手動編輯 wav。"""
import math
import os
import random
import struct
import wave

RATE = 22050
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "sfx")


def write_wav(name: str, samples: list[float]) -> None:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
            for s in samples)
        w.writeframes(frames)
    print(f"OK: {path}（{len(samples) / RATE:.2f}s）")


def env(i: int, n: int, attack: float = 0.02, decay: float = 1.0) -> float:
    """簡單 AD 包絡。"""
    t = i / n
    a = min(1.0, t / attack) if attack > 0 else 1.0
    return a * math.exp(-decay * 4 * t)


def laser() -> list[float]:
    """雷射：高頻下滑鋸齒掃頻 0.30s。"""
    n = int(RATE * 0.30)
    out = []
    phase = 0.0
    for i in range(n):
        f = 1800 - 1300 * (i / n)
        phase += f / RATE
        saw = 2 * (phase % 1.0) - 1
        out.append(0.5 * saw * env(i, n, attack=0.01, decay=0.8))
    return out


def hit() -> list[float]:
    """命中：白噪音爆裂 + 低頻衝擊 0.35s。"""
    rng = random.Random(7)
    n = int(RATE * 0.35)
    out = []
    for i in range(n):
        noise = rng.uniform(-1, 1)
        thump = math.sin(2 * math.pi * 70 * i / RATE)
        out.append((0.6 * noise + 0.5 * thump) * env(i, n, attack=0.0, decay=1.6))
    return out


def _tone_seq(freqs: list[float], dur: float) -> list[float]:
    out = []
    n = int(RATE * dur)
    for f in freqs:
        for i in range(n):
            s = 0.4 * math.sin(2 * math.pi * f * i / RATE)
            s += 0.15 * math.sin(2 * math.pi * f * 2 * i / RATE)
            out.append(s * env(i, n, attack=0.05, decay=0.9))
    return out


def win() -> list[float]:
    return _tone_seq([523.25, 659.25, 783.99, 1046.5], 0.16)   # C E G C 上行


def lose() -> list[float]:
    return _tone_seq([392.0, 311.13, 233.08], 0.22)            # 下行小三度


def click() -> list[float]:
    n = int(RATE * 0.04)
    return [0.3 * math.sin(2 * math.pi * 900 * i / RATE) * env(i, n, 0.0, 3.0)
            for i in range(n)]


def main() -> None:
    write_wav("laser", laser())
    write_wav("hit", hit())
    write_wav("win", win())
    write_wav("lose", lose())
    write_wav("click", click())


if __name__ == "__main__":
    main()
