import asyncio
import speech_recognition as sr
from bleak import BleakClient
import sounddevice as sd
import numpy as np
import platform

# Bluetooth configuration
ARDUINO_ADDR = "78:21:84:7b:3b:c2"
CHARACTERISTIC_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"

# Audio configuration
SAMPLE_RATE = 16000
DURATION = 5

IS_WINDOWS = platform.system() == "Windows"

def record_audio():
    """Record audio from microphone"""
    print("Listening...")
    audio_data = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE, channels=1, dtype=np.int16)
    sd.wait()
    return sr.AudioData(audio_data.tobytes(), SAMPLE_RATE, 2)

def find_command(text):
    """Identify command from recognized text"""
    text = text.lower()
    print(f"Identifying command from: {text}")

    if "bathroom" in text:
        print("Bathroom command detected")
        return "BATHROOM_ON"
    elif "hallway" in text:
        print("Hallway command detected")
        return "HALLWAY_ON"
    elif "fan" in text:
        print("Fan command detected")
        return "FAN_ON"
    elif "off" in text:
        print("All off command detected")
        return "ALL_OFF"
    elif "on" in text:
        print("All on command detected")
        return "ALL_ON"
    return None

# ----Windows  --------------------------------------------------------------------------------

async def _send_ble_command_once(command):
    """Connect, send, disconnect — used on Windows per-command"""
    async with BleakClient(ARDUINO_ADDR) as client:
        print(f"Connected to {ARDUINO_ADDR}")
        await client.write_gatt_char(CHARACTERISTIC_UUID, command.encode())
        print(f"Sent: {command}")

def _send_command_sync(command):
    """Run BLE send in a fresh event loop (Windows thread pool)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_send_ble_command_once(command))
    finally:
        loop.close()

async def windows_main():
    """Windows: reconnects on every command due to threading constraints"""
    from concurrent.futures import ThreadPoolExecutor
    recognizer = sr.Recognizer()
    executor = ThreadPoolExecutor(max_workers=1)
    loop = asyncio.get_event_loop()
    print("Voice-activated lighting system started (Windows mode).\n")

    while True:
        try:
            audio = record_audio()
            text = recognizer.recognize_google(audio).lower()
            print(f"Heard: {text}")

            command = find_command(text)
            if command:
                await loop.run_in_executor(executor, _send_command_sync, command)
            else:
                print("No matching command found.")

        except sr.UnknownValueError:
            print("Could not understand audio, try again.")
        except sr.RequestError as e:
            print(f"Speech recognition service error: {e}")
        except KeyboardInterrupt:
            print("\nExiting.")
            executor.shutdown(wait=False)
            break

#------ Linux / Pi -------------------------------------------------------------------------

async def pi_main():
    
    recognizer = sr.Recognizer()
    print("Voice-activated lighting system started (Pi mode).")
    print(f"Connecting to: {ARDUINO_ADDR}")

    async with BleakClient(ARDUINO_ADDR) as client:
        print("Connected. Ready for voice commands.\n")

        while True:
            try:
                audio = record_audio()
                text = recognizer.recognize_google(audio).lower()
                print(f"Heard: {text}")

                command = find_command(text)
                if command:
                    await client.write_gatt_char(CHARACTERISTIC_UUID, command.encode())
                    print(f"Sent: {command}")
                else:
                    print("No matching command found.")

            except sr.UnknownValueError:
                print("Could not understand audio, try again.")
            except sr.RequestError as e:
                print(f"Speech recognition service error: {e}")
            except KeyboardInterrupt:
                print("\nExiting.")
                break




if __name__ == "__main__":
    if IS_WINDOWS:
        asyncio.run(windows_main())
    else:
        asyncio.run(pi_main())