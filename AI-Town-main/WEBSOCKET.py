import io
import json
import base64
import asyncio
import websockets
from PIL import Image

from world.world_clock import WorldClock
from agent.manager import AgentManager
from model.model_loader import ModelLoader


last_sent_time = None
clients = {
    "UE": None,
    "YOLO": None,
}

status = {
    "system_started": False,
}

manager = None
state_by_name = {}
name_to_code = {}
tick_lock = asyncio.Lock()

def format_time_hhmmss(time_str: str) -> str:
    # manager 回傳通常是 HH:MM
    if len(time_str.split(":")) == 2:
        return f"{time_str}:00"
    return time_str

async def send_time_to_ue_if_changed(tick_data: dict):
    global last_sent_time

    time_str = tick_data.get("time")
    if not time_str:
        return

    time_hhmmss = format_time_hhmmss(time_str)

    if time_hhmmss == last_sent_time:
        return

    last_sent_time = time_hhmmss

    await send_to_ue({
        "event": "time",
        "data": time_hhmmss,
    })

def build_system():
    loader = ModelLoader()
    loader.load()

    clock = WorldClock()
    mgr = AgentManager(loader, clock)
    return mgr


def init_character_states(mgr):
    global state_by_name, name_to_code

    state_by_name = {}
    name_to_code = {}

    from config.action_list import action_id_resolver

    for code in mgr.all_codes():
        char = mgr.get_character(code)
        name_to_code[char.name] = code

        # 解析初始動作的 ActionID
        action_id = action_id_resolver(
            abstract_verb=char.current_action,
            char_code=code,
            current_location=char.current_location
        )

        state_by_name[code] = {
            "name": char.name,
            "location": char.current_location,
            "action": str(action_id) if action_id is not None else "",
        }

    print("Initial character states:")
    print(json.dumps(state_by_name, ensure_ascii=False, indent=2))


async def send_to_ue(payload: dict):
    ws = clients.get("UE")
    if not ws:
        return

    try:
        msg = json.dumps(payload, ensure_ascii=False)
        print(f"傳給ue: {msg}")
        await ws.send(msg)
    except Exception:
        print("Failed to send message to UE.")
        clients["UE"] = None
        status["system_started"] = False


async def request_frame_from_yolo(character_name: str):
    ws = clients.get("YOLO")
    if not ws:
        print("YOLO client is not connected.")
        return

    payload = {
        "event": "request_frame",
        "character": character_name,
    }

    try:
        await ws.send(json.dumps(payload, ensure_ascii=False))
        print(f"Requested current frame from YOLO: {character_name}")
    except Exception:
        print("Failed to send request_frame to YOLO.")
        clients["YOLO"] = None
        status["system_started"] = False


def format_dialogue_for_ue(dialogue: dict):
    if not dialogue.get("accepted", False):
        return None

    initiator = dialogue.get("initiator")
    responder = dialogue.get("responder")
    turns = dialogue.get("turns", [])

    data = []

    for turn in turns:
        speaker_code = turn.get("speaker")
        text = turn.get("msg", "")

        if speaker_code == initiator:
            listener_code = responder
        else:
            listener_code = initiator

        data.append({
            "speaker": str(speaker_code),
            "listener": str(listener_code),
            "text": text,
        })

    return {
        "event": "Dialogue",
        "data": data,
    }


async def send_tick_result_to_ue(tick_data: dict):
    # 1. 處理並傳送對話事件
    for dialogue in tick_data.get("dialogues", []):
        payload = format_dialogue_for_ue(dialogue)
        if payload:
            await send_to_ue(payload)
            await asyncio.sleep(0.1)  # 每個對話 JSON 發送後延遲 0.1 秒

    # 2. 處理並傳送非對話行動事件
    for code, dec in tick_data.get("decide", {}).items():
        action = dec.get("action")
        action_id = dec.get("action_id")

        # 如果行動是對話，跳過發送 Action 事件，改由對話事件處理
        if action == "對話" or action_id == 45 or action_id is None:
            continue

        await send_to_ue({
            "event": "action",
            "character": str(code),
            "actionID": str(action_id),
        })
        await asyncio.sleep(0.1)


async def run_tick_with_yolo_image(character_name: str, image: Image.Image):
    global state_by_name

    if manager is None:
        print("Manager is not initialized.")
        return

    code = name_to_code.get(character_name)
    if not code:
        print(f"Unknown character: {character_name}")
        return

    char = manager.get_character(code)

    perception_input = {
        code: {
            "location": char.current_location,
            "yolo_desc": ["person"],
            "scene_text": f"{character_name} sees a person nearby.",
        }
    }

    image_input = {
        code: image,
    }

    async with tick_lock:
        tick_data = await asyncio.to_thread(
            manager.run_tick,
            perception_input,
            {},
        )

    changed_states = []

    for c in manager.all_codes():
        ch = manager.get_character(c)

        from config.action_list import action_id_resolver
        action_id = action_id_resolver(
            abstract_verb=ch.current_action,
            char_code=c,
            current_location=ch.current_location
        )

        new_state = {
            "name": ch.name,
            "location": ch.current_location,
            "action": str(action_id) if action_id is not None else "",
        }

        old_state = state_by_name.get(c)
        state_by_name[c] = new_state

        if old_state is None or old_state.get("action") != new_state["action"]:
            changed_states.append(new_state)

    await send_time_to_ue_if_changed(tick_data)
    await send_tick_result_to_ue(tick_data)
    

    print("Tick completed.")
    print(json.dumps({
        "character": character_name,
        "changed_states": changed_states,
        "tick": tick_data.get("tick"),
        "time": tick_data.get("time"),
        "day": tick_data.get("day"),
        "dialogues": tick_data.get("dialogues", []),
    }, ensure_ascii=False, indent=2))


async def handle_yolo_frame(data: dict):
    try:
        character_name = data["character"]
        img_b64 = data["image"]

        img_bytes = base64.b64decode(img_b64)
        image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        print(f"Received frame_response from YOLO: {character_name}")

        await run_tick_with_yolo_image(character_name, image)

    except Exception as e:
        print(f"Failed to handle YOLO frame_response: {e}")


async def handler(websocket):
    print(f"New connection: {websocket.remote_address}")

    try:
        async for message in websocket:
            if message == "UE_standby":
                clients["UE"] = websocket
                print("UE is ready.")

                for code, state in state_by_name.items():
                    action_id = state.get("action")
                    if action_id:
                        await send_to_ue({
                            "event": "action",
                            "character": str(code),
                            "actionID": str(action_id),
                        })
                        await asyncio.sleep(0.1)

            elif message == "YOLO_standby":
                clients["YOLO"] = websocket
                print("YOLO is ready.")

            if clients["UE"] and clients["YOLO"] and not status["system_started"]:
                status["system_started"] = True
                print("System started: UE and YOLO are connected.")

            if isinstance(message, str) and message.startswith("{"):
                try:
                    packet = json.loads(message)
                    event = packet.get("event")

                    if event == "person_detected":
                        character_name = packet.get("character")
                        if character_name:
                            await request_frame_from_yolo(character_name)

                    elif event == "frame_response":
                        asyncio.create_task(handle_yolo_frame(packet))

                except Exception as e:
                    print(f"Failed to parse JSON message: {e}")

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed: {websocket.remote_address}")

    finally:
        if clients["UE"] == websocket:
            clients["UE"] = None
            status["system_started"] = False
            print("UE disconnected.")

        if clients["YOLO"] == websocket:
            clients["YOLO"] = None
            status["system_started"] = False
            print("YOLO disconnected.")


async def main():
    global manager

    print("Initializing AI system...")
    manager = await asyncio.to_thread(build_system)
    init_character_states(manager)

    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket server running on port 8765.")
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.")