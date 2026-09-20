"""
程序合成音效系统
使用纯数学波形与 Python 标准库 wave 生成轻量无外部依赖的 PCM 音效
包含消除飞出音、碰撞受阻音、过关胜利音、失败音与提示音
"""

import io
import math
import os
import struct
import wave
from typing import Optional
import pygame


class SoundManager:
    """音效与背景音乐管理器（程序化音效 + 赛博合成波 BGM）"""

    def __init__(self):
        self.enabled = True
        self.music_enabled = True
        self.music_volume = 0.32
        self.music_playing = False
        self.music_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "assets", "audio", "bgm_synthwave.ogg")
        )
        self.sounds = {}
        self._init_mixer()

    def _init_mixer(self):
        """初始化音频混音器并生成波形"""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._generate_procedural_sounds()
        except Exception as e:
            print(f"[SoundManager] 音频设备不可用，已静音运行: {e}")
            self.enabled = False

    def _create_wav_bytes(self, samples: list, sample_rate: int = 44100) -> io.BytesIO:
        """将数值采样列表打包为标准内存 WAV 二进制流"""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            # 限制在 [-32767, 32767]
            packed = bytearray()
            for s in samples:
                val = max(-32767, min(32767, int(s)))
                packed.extend(struct.pack("<h", val))
            wf.writeframes(packed)
        buf.seek(0)
        return buf

    def _generate_procedural_sounds(self):
        """生成全部音效"""
        sr = 44100

        # 1. 成功飞出音 (Fly / Whoosh): 快速上扬的正弦波扫频 (400Hz -> 900Hz)
        fly_duration = 0.22
        n_samples = int(sr * fly_duration)
        fly_samples = []
        for i in range(n_samples):
            t = i / sr
            progress = i / n_samples
            freq = 400.0 + 500.0 * (progress ** 1.5)
            # 包络：快速 attack, 慢 decay
            env = math.sin(progress * math.pi)
            sample = 16000.0 * env * math.sin(2.0 * math.pi * freq * t)
            fly_samples.append(sample)
        self.sounds["fly"] = pygame.mixer.Sound(self._create_wav_bytes(fly_samples, sr))
        self.sounds["fly"].set_volume(0.4)

        # 2. 碰撞受阻音 (Blocked / Bump): 低频下潜顿挫波 (180Hz -> 80Hz) + 微量泛音
        bump_duration = 0.18
        n_samples = int(sr * bump_duration)
        bump_samples = []
        for i in range(n_samples):
            t = i / sr
            progress = i / n_samples
            freq = max(60.0, 180.0 - 120.0 * progress)
            env = math.exp(-12.0 * progress)
            # 基频 + 二次谐波模拟木质敲击声
            sample = 22000.0 * env * (
                math.sin(2.0 * math.pi * freq * t) + 0.4 * math.sin(4.0 * math.pi * freq * t)
            )
            bump_samples.append(sample)
        self.sounds["blocked"] = pygame.mixer.Sound(self._create_wav_bytes(bump_samples, sr))
        self.sounds["blocked"].set_volume(0.6)

        # 3. 点击按钮音 (Click): 极短高频清脆点触 (880Hz)
        click_duration = 0.04
        n_samples = int(sr * click_duration)
        click_samples = []
        for i in range(n_samples):
            progress = i / n_samples
            env = math.exp(-25.0 * progress)
            sample = 12000.0 * env * math.sin(2.0 * math.pi * 880.0 * (i / sr))
            click_samples.append(sample)
        self.sounds["click"] = pygame.mixer.Sound(self._create_wav_bytes(click_samples, sr))
        self.sounds["click"].set_volume(0.3)

        # 4. 提示音 (Hint): 优雅的双音铃声 (E6 -> A6)
        hint_duration = 0.3
        n_samples = int(sr * hint_duration)
        hint_samples = []
        for i in range(n_samples):
            t = i / sr
            progress = i / n_samples
            freq = 1318.5 if progress < 0.4 else 1760.0
            env = math.exp(-6.0 * (progress if progress < 0.4 else (progress - 0.4)))
            sample = 14000.0 * env * math.sin(2.0 * math.pi * freq * t)
            hint_samples.append(sample)
        self.sounds["hint"] = pygame.mixer.Sound(self._create_wav_bytes(hint_samples, sr))
        self.sounds["hint"].set_volume(0.4)

        # 5. 通关胜利音 (Victory): 欢快大三和弦琶音 (C5-E5-G5-C6)
        win_duration = 0.7
        n_samples = int(sr * win_duration)
        win_samples = []
        notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
        for i in range(n_samples):
            t = i / sr
            progress = i / n_samples
            note_idx = min(len(notes) - 1, int(progress * 4.5))
            freq = notes[note_idx]
            sub_prog = (progress * 4.5) % 1.0
            env = math.exp(-4.0 * sub_prog)
            sample = 18000.0 * env * math.sin(2.0 * math.pi * freq * t)
            win_samples.append(sample)
        self.sounds["win"] = pygame.mixer.Sound(self._create_wav_bytes(win_samples, sr))
        self.sounds["win"].set_volume(0.5)

        # 6. 失败音 (Game Over): 哀伤下行短音 (A4 -> F4 -> D4)
        fail_duration = 0.6
        n_samples = int(sr * fail_duration)
        fail_samples = []
        fail_notes = [440.0, 349.23, 293.66]
        for i in range(n_samples):
            t = i / sr
            progress = i / n_samples
            note_idx = min(len(fail_notes) - 1, int(progress * 3.0))
            freq = fail_notes[note_idx]
            sub_prog = (progress * 3.0) % 1.0
            env = math.exp(-3.5 * sub_prog)
            sample = 18000.0 * env * math.sin(2.0 * math.pi * freq * t)
            fail_samples.append(sample)
        self.sounds["fail"] = pygame.mixer.Sound(self._create_wav_bytes(fail_samples, sr))
        self.sounds["fail"].set_volume(0.5)

    def play(self, sound_name: str):
        """播放指定音效"""
        if not self.enabled or sound_name not in self.sounds:
            return
        try:
            self.sounds[sound_name].play()
        except Exception:
            pass

    def toggle_sound(self) -> bool:
        """切换音效开启/关闭"""
        self.enabled = not self.enabled
        return self.enabled

    def play_bgm(self, loop: bool = True, fade_ms: int = 1200):
        """播放赛博合成波背景音乐（支持无缝循环与淡入）"""
        if not self.music_enabled:
            return
        if not os.path.exists(self.music_path):
            return
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.set_volume(self.music_volume)
                self.music_playing = True
                return
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.set_volume(self.music_volume)
            loops = -1 if loop else 0
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self.music_playing = True
        except Exception as e:
            print(f"[SoundManager] 无法播放背景音乐: {e}")

    def stop_bgm(self, fade_ms: int = 600):
        """停止背景音乐"""
        try:
            pygame.mixer.music.fadeout(fade_ms)
            self.music_playing = False
        except Exception:
            pass

    def pause_bgm(self):
        """暂停背景音乐"""
        try:
            pygame.mixer.music.pause()
            self.music_playing = False
        except Exception:
            pass

    def unpause_bgm(self):
        """恢复背景音乐播放"""
        if not self.music_enabled:
            return
        try:
            pygame.mixer.music.unpause()
            self.music_playing = True
        except Exception:
            pass

    def toggle_music(self) -> bool:
        """切换背景音乐播放/静音状态"""
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            if not pygame.mixer.music.get_busy():
                self.play_bgm(loop=True)
            else:
                self.unpause_bgm()
        else:
            self.pause_bgm()
        return self.music_enabled

    def set_music_volume(self, volume: float):
        """设置背景音乐音量 (0.0 ~ 1.0)"""
        self.music_volume = max(0.0, min(1.0, volume))
        try:
            pygame.mixer.music.set_volume(self.music_volume)
        except Exception:
            pass

