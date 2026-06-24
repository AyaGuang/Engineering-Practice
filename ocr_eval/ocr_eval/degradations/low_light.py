"""ocr_eval.degradations.low_light - 低光照 + 色温偏移 + 暗角 + 感光噪点

模拟：台灯光线不足 + 暖色调 + 桌面光照不均 + 高 ISO 噪点
物理依据：低光照下相机自动拉高 ISO，感光元件噪点同步增加
场景：晚上台灯下拍作业、阴影中的纸张

* create by 林文光
* copyright USTC
* 2026.06.23
"""
import numpy as np

from .base import BaseDegradation


class LowLightDegradation(BaseDegradation):
    name = "low_light"

    def __init__(
        self,
        brightness: float = 0.5,         # 亮度倍率 0-1
        color_temp_k: int = 2800,         # 色温 K，<4000 为暖色
        vignette_strength: float = 0.4,   # 暗角强度 0-1
        noise_std: float = 8.0,           # 高斯噪点标准差（亮度越低噪点越显眼）
        noise_seed: int | None = 42,      # 噪点随机种子（可复现）
        **kwargs,
    ) -> None:
        self.brightness = brightness
        self.color_temp_k = color_temp_k
        self.vignette_strength = vignette_strength
        self.noise_std = noise_std
        self.noise_seed = noise_seed
        self._rng = np.random.default_rng(noise_seed)

    def apply(self, img: np.ndarray) -> np.ndarray:
        out = img.astype(np.float32) * self.brightness

        # 1) 模拟低色温暖色调（黄红偏移）
        if self.color_temp_k < 4000:
            warm = (4000 - self.color_temp_k) / 4000.0
            out[..., 2] *= (1 + 0.15 * warm)   # R
            out[..., 1] *= (1 + 0.08 * warm)   # G
            out[..., 0] *= (1 - 0.10 * warm)   # B

        # 2) 模拟暗角（径向光照衰减）
        if self.vignette_strength > 0:
            h, w = img.shape[:2]
            Y, X = np.ogrid[:h, :w]
            cy, cx = h / 2, w / 2
            dist = np.sqrt(((Y - cy) / cy) ** 2 + ((X - cx) / cx) ** 2)
            mask = 1 - self.vignette_strength * np.clip(dist, 0, 1)
            out = out * mask[..., None]

        # 3) 加入高斯感光噪点（低光下 ISO 拉高 → 噪点明显）
        if self.noise_std > 0:
            noise = self._rng.normal(0, self.noise_std, out.shape).astype(np.float32)
            out = out + noise

        return out.clip(0, 255).astype(np.uint8)
