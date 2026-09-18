import uuid
import time
import threading

import pychromecast
from pychromecast.models import CastInfo, HostServiceInfo
from pychromecast.const import CAST_TYPE_AUDIO


def discover_devices(timeout: int = 5) -> list[dict]:
    """
    Chromecast デバイスを探索

    Args:
        timeout: 探索タイムアウト (秒)

    Returns:
        見つかったデバイス情報のリスト
    """
    chromecasts, browser = pychromecast.discovery.discover_chromecasts(timeout=timeout)
    pychromecast.discovery.stop_discovery(browser)

    devices = []
    for cc in chromecasts:
        devices.append(
            {
                "address": cc.host,
                "port": cc.port,
                "friendly_name": cc.friendly_name,
                "model_name": cc.model_name,
                "cast_type": cc.cast_type,
            }
        )
    return devices


def print_devices(devices: list[dict]) -> None:
    if not devices:
        print("Not found.")
        return

    print(f"\n見つかったデバイス ({len(devices)} 個):")
    print("-" * 80)
    for d in devices:
        print(f"  Name: {d['friendly_name'] or d['model_name'] or 'Unknown'}")
        print(f"  Address: {d['address']}")
        print(f"  Port: {d['port']}")
        print(f"  Type: {d['cast_type']}")
        print(f"  Model: {d['model_name']}")
        print()


class GoogleHomePlayer:
    """Google Home/Chromecast デバイス制御"""

    def __init__(self, address: str, port: int = 8009):
        """
        Args:
            address: Google Home のアドレス
            port: Google Home のポート (デフォルト: 8009)
        """
        self.address = address
        self.port = port
        self.device: pychromecast.Chromecast | None = None

    def connect(self) -> tuple[bool, str]:
        """Google Home/Chromecast に接続"""
        try:
            cast_info = CastInfo(
                services={HostServiceInfo(host=self.address, port=self.port)},
                uuid=uuid.uuid4(),
                model_name=None,
                friendly_name=None,
                host=self.address,
                port=self.port,
                cast_type=CAST_TYPE_AUDIO,
                manufacturer=None,
            )
            self.device = pychromecast.get_chromecast_from_cast_info(
                cast_info, zconf=None
            )
            self.device.wait()
            return True, "Connected"
        except Exception as e:
            self.device = None
            return False, str(e)

    def play_media(self, audio_url: str, content_type:str= "audio/mpeg", volume: float | None = None) -> tuple[bool, str]:
        if not self.device:
            connected, msg = self.connect()
            if not connected:
                return False, msg

        try:
            assert self.device, "The device is not connected."

            original_volume = None
            if volume is not None:
                original_volume = self.get_volume_level()
                self.set_volume_level(volume)

            mc = self.device.media_controller
            mc.play_media(audio_url, content_type)

            if volume is not None:
                threading.Thread(
                    target=self._wait_for_playback_and_restore_volume,
                    args=(original_volume,),
                    daemon=True,
                ).start()
                return True, "Success"
            else:
                mc.block_until_active()
                return True, "Success"
        except Exception as e:
            if volume is not None and original_volume is not None:
                try:
                    self.set_volume_level(original_volume)
                except Exception:
                    pass
            return False, str(e)

    def _wait_for_playback_and_restore_volume(self, original_volume: float | None) -> None:
        self._wait_for_playback()

        if original_volume is not None:
            try:
                self.set_volume_level(original_volume)
            except Exception:
                pass

    def _wait_for_playback(self) -> bool:
        """再生が完了した、あるいは再生開始が確認できなかったら制御を戻す

        Returns:
            再生が開始できたか (PLAYING or BUFFERING に遷移したか)
        """
        timeout_seconds = 3
        poll_interval = 0.1
        elapsed = 0
        started = False

        while elapsed < timeout_seconds:
            try:
                status = self.get_media_controller_status()
                if status:
                    player_state = status.player_state

                    if player_state in ("PLAYING", "BUFFERING"):
                        started = True

                    if started and player_state == "IDLE":
                        idle_reason = status.idle_reason
                        if idle_reason == "FINISHED":
                            return True

                time.sleep(poll_interval)
                elapsed += poll_interval
            except Exception:
                pass

        return started

    def get_volume_level(self) -> float | None:
        assert self.device, "The device is not connected."
        status = self.device.status
        if status:
            return status.volume_level
        return None

    def set_volume_level(self, volume_level: float):
        assert self.device, "The device is not connected."
        self.device.set_volume(volume_level)

    def get_media_controller_status(self):
        assert self.device, "The device is not connected."
        mc = self.device.media_controller
        return mc.status


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Discover Chromecast devices")
    parser.add_argument("--timeout", type=int, default=5, help="Timeout (s)")
    args = parser.parse_args()

    print("Browsing...")
    try:
        devices = discover_devices(timeout=args.timeout)
        print_devices(devices)
    except Exception as e:
        print(f"Error: {e}")
