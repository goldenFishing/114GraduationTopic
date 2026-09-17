import socket
import struct
import sys
import time
import numpy as np
import cv2
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QGridLayout
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
import torchreid
from io import BytesIO
from PIL import Image
import asyncio
import websockets
import json
import base64
from ai_pipeline import ReIDDatabase, MOTReIDPipeline
import torch
import os



UDP_PORT = 9000
WS_URI = "ws://127.0.0.1:8765"

udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.bind(("0.0.0.0", UDP_PORT))
udp_sock.setblocking(False)


CHAR_ID_TO_NAME = {
    1: "Amy",
    2: "Ben",
    3: "Claire",
    4: "David",
    5: "Emma",
}


def decode_jpeg_packet(data: bytes):
    if len(data) < 12:
        return None

    char_id, w, h = struct.unpack("<iii", data[:12])
    jpeg_bytes = data[12:]

    try:
        image = Image.open(BytesIO(jpeg_bytes)).convert("RGB")
        img_np = np.array(image)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        return char_id, img_bgr
    except Exception:
        return None


def frame_to_base64_jpg(frame_bgr: np.ndarray) -> str:
    ok, buffer = cv2.imencode(".jpg", frame_bgr)
    if not ok:
        raise RuntimeError("Failed to encode frame as JPG.")
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


class WebSocketClient:
    def __init__(self):
        self.ws = None
        self.window = None
        self.running = True

    def bind_window(self, window):
        self.window = window

    async def connect_loop(self):
        while self.running:
            try:
                print(f"🔌 Connecting to WebSocket server: {WS_URI}")
                async with websockets.connect(WS_URI) as websocket:
                    self.ws = websocket
                    await websocket.send("YOLO_standby")
                    print("✅ Sent YOLO_standby")

                    async for message in websocket:
                        await self.handle_message(message)

            except Exception as e:
                print(f"⚠️ WebSocket disconnected/retry later: {e}")
                self.ws = None
                await asyncio.sleep(2)

    async def handle_message(self, message: str):
        try:
            data = json.loads(message)
        except Exception:
            print(f"⚠️ Non-JSON message from server: {message}")
            return

        event = data.get("event")

        if event == "request_frame":
            character_name = data.get("character")
            await self.send_frame_response(character_name)

    async def send_person_detected(self, character_name: str, people: list):
        if not self.ws:
            return

        payload = {
            "event": "person_detected",
            "character": character_name,
            "people": people,
        }

        try:
            await self.ws.send(json.dumps(payload, ensure_ascii=False))
            print(f"📤 Sent person_detected: {character_name}, people={people}")
        except Exception as e:
            print(f"⚠️ Failed to send person_detected: {e}")

    async def send_frame_response(self, character_name: str):
        if not self.ws or not self.window:
            return

        char_id = None
        for cid, name in CHAR_ID_TO_NAME.items():
            if name == character_name:
                char_id = cid
                break

        if char_id is None:
            print(f"⚠️ Unknown character requested: {character_name}")
            return

        frame = self.window.get_latest_frame(char_id)
        if frame is None:
            print(f"⚠️ No frame available for {character_name}")
            return

        try:
            img_b64 = frame_to_base64_jpg(frame)

            payload = {
                "event": "frame_response",
                "character": character_name,
                "image": img_b64,
            }

            await self.ws.send(json.dumps(payload, ensure_ascii=False))
            print(f"📤 Sent frame_response: {character_name}")

        except Exception as e:
            print(f"⚠️ Failed to send frame_response: {e}")


class AIInferenceWorker(QThread):
    frame_processed = pyqtSignal(int, np.ndarray, bool, list)

    def __init__(self, char_id, pipeline):
        super().__init__()
        self.char_id = char_id
        self.pipeline = pipeline
        self.current_frame = None
        self.running = True

    def run(self):
        while self.running:
            if self.current_frame is not None:
                frame_to_process = self.current_frame.copy()
                self.current_frame = None

                processed_frame, detected_people = self.pipeline.process_frame(frame_to_process)

                person_detected = len(detected_people) > 0

                self.frame_processed.emit(
                    self.char_id,
                    processed_frame,
                    person_detected,
                    detected_people,
                )
            else:
                self.msleep(5)

    def update_frame(self, frame):
        self.current_frame = frame

    def stop(self):
        self.running = False
        self.wait()


class SimpleStreamWindow(QWidget):
    def __init__(self, ws_client: WebSocketClient):
        super().__init__()

        self.ws_client = ws_client
        self.ws_client.bind_window(self)

        self.setWindowTitle("PyQt YOLO/ReID WebSocket Client")
        self.setGeometry(100, 100, 1280, 720)

        print("🚀 Loading OSNet model and ReID database...")

        self.reid_model = torchreid.models.build_model(
            name="osnet_x1_0",
            num_classes=1000,
            loss="softmax",
            pretrained=True,
        )
        self.reid_model.eval()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        clean_db_folder = os.path.join(script_dir, "reid_clean_gallery")

        self.db = ReIDDatabase(
            clean_db_folder=clean_db_folder,
            reid_model=self.reid_model,
        )

        self.labels = {}
        grid = QGridLayout()

        for i in range(1, 6):
            img_label = QLabel(f"Waiting for ID {i}...")
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setStyleSheet(
                "background-color: #111; color: #555; border: 2px solid #333;"
            )
            img_label.setMinimumSize(320, 180)
            self.labels[i] = img_label
            grid.addWidget(img_label, (i - 1) // 3, (i - 1) % 3)

        self.setLayout(grid)

        self.frame_buffer = {i: None for i in range(1, 6)}
        self.raw_frame_buffer = {i: None for i in range(1, 6)}
        self.prev_time = {i: 0 for i in range(1, 6)}
        self.fps_display = {i: 0 for i in range(1, 6)}

        self.detect_count = {i: 0 for i in range(1, 6)}
        self.detect_notified = {i: False for i in range(1, 6)}

        self.ai_workers = {}
        for i in range(1, 6):
            pipeline = MOTReIDPipeline(db=self.db, reid_model=self.reid_model)
            worker = AIInferenceWorker(char_id=i, pipeline=pipeline)
            worker.frame_processed.connect(self.on_ai_frame_ready)
            worker.start()
            self.ai_workers[i] = worker

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(33)

        self.receiver = QTimer()
        self.receiver.timeout.connect(self.receive_udp)
        self.receiver.start(1)

    def get_latest_frame(self, char_id: int):
        frame = self.raw_frame_buffer.get(char_id)
        if frame is not None:
            return frame
        return self.frame_buffer.get(char_id)

    def on_ai_frame_ready(self, char_id, processed_frame, person_detected, detected_people):
        curr_time = time.time()
        diff = curr_time - self.prev_time[char_id]

        if diff > 0:
            self.fps_display[char_id] = 1.0 / diff

        self.prev_time[char_id] = curr_time

        fps_text = f"ID: {char_id} | AI FPS: {self.fps_display[char_id]:.1f}"
        cv2.putText(
            processed_frame,
            fps_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

        self.frame_buffer[char_id] = processed_frame

        if person_detected:
            self.detect_count[char_id] += 1
        else:
            self.detect_count[char_id] = 0
            self.detect_notified[char_id] = False

        if self.detect_count[char_id] >= 10 and not self.detect_notified[char_id]:
            self.detect_notified[char_id] = True
            character_name = CHAR_ID_TO_NAME.get(char_id, str(char_id))

            asyncio.create_task(
                self.ws_client.send_person_detected(
                    character_name,
                    detected_people,
                )
            )

    def receive_udp(self):
        while True:
            try:
                data, _ = udp_sock.recvfrom(65535)
                result = decode_jpeg_packet(data)

                if result:
                    char_id, frame = result

                    self.raw_frame_buffer[char_id] = frame

                    if char_id in self.ai_workers:
                        self.ai_workers[char_id].update_frame(frame)

            except BlockingIOError:
                break
            except Exception as e:
                print(f"UDP Error: {e}")
                break

    def update_ui(self):
        for char_id, label in self.labels.items():
            frame = self.frame_buffer.get(char_id)

            if frame is not None:
                h, w, ch = frame.shape
                qimg = QImage(
                    frame.data,
                    w,
                    h,
                    ch * w,
                    QImage.Format.Format_BGR888,
                )
                pixmap = QPixmap.fromImage(qimg).scaled(
                    label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(pixmap)

    def closeEvent(self, event):
        for worker in self.ai_workers.values():
            worker.stop()
        self.ws_client.running = False
        super().closeEvent(event)


async def main():
    ws_client = WebSocketClient()
    asyncio.create_task(ws_client.connect_loop())

    app = QApplication(sys.argv)

    window = SimpleStreamWindow(ws_client=ws_client)
    window.show()

    print("🖥️ UI started. Waiting for UDP stream...")

    while window.isVisible():
        app.processEvents()
        await asyncio.sleep(0.01)

    print("🛑 Window closed. Exiting...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Program stopped by keyboard.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")