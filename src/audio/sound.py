"""
程序合成音效系统
使用纯数学波形与 Python 标准库 wave 生成轻量无外部依赖的 PCM 音效
包含消除飞出音、碰撞受阻音、过关胜利音、失败音与提示音
"""

import io
import math
import os
import random
import struct
import sys
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
        base_dir = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
        self.music_path = os.path.abspath(
            os.path.join(base_dir, "assets", "audio", "bgm_synthwave.ogg")
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

        # 2. 赛博碰撞受阻音 (Blocked / Cyber Deflect):
        # 尖锐高科技金属接触冲击 + FM 能量偏折共鸣 + 顿挫低频抗阻重音
        bump_duration = 0.22
        n_samples = int(sr * bump_duration)
        bump_samples = []
        # 固定随机种子确保音频波形确切且一致
        rng = random.Random(42)
        for i in range(n_samples):
            t = i / sr
            progress = i / n_samples
            # 1. 瞬态冲击火花微爆（前 20ms）
            transient_env = math.exp(-45.0 * progress)
            spark_noise = (rng.random() * 2.0 - 1.0) * transient_env * 0.35

            # 2. 能量共振主体：FM 调制金属偏振声 (基础频率 580Hz -> 160Hz 快速衰减)
            base_freq = 580.0 * math.exp(-12.0 * progress) + 160.0
            fm_mod = 3.5 * math.exp(-22.0 * progress) * math.sin(2.0 * math.pi * 840.0 * t)
            metal_body = math.sin(2.0 * math.pi * base_freq * t + fm_mod) * math.exp(-14.0 * progress)

            # 3. 顿挫低频阻尼 (90Hz 充沛底鼓质感)
            sub_punch = math.sin(2.0 * math.pi * 90.0 * t) * math.exp(-10.0 * progress) * 0.45

            sample = 26000.0 * (metal_body * 0.75 + spark_noise + sub_punch)
            bump_samples.append(sample)
        self.sounds["blocked"] = pygame.mixer.Sound(self._create_wav_bytes(bump_samples, sr))
        self.sounds["blocked"].set_volume(0.65)

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

