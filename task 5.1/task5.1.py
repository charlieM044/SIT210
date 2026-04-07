

import tkinter as tk

try:
    import RPi.GPIO as GPIO
    LED_PINS = [17, 27, 22]  # GPIO pins for the LEDs

    GPIO.setmode(GPIO.BCM)
    for pin in LED_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
  
except ImportError:
    print("RPi.GPIO library not found. GPIO functionality will be disabled.")
    LED_PINS = [1,2,3]  # Dummy pins for testing without GPIO

class led_Chanel:
    def __init__(self, pin):
        self.pin = pin
        self.state = False

    
class LEDControlApp:
    def __init__(self, master):
        self.master = master
        self.master.title("LED Control App")
        self.led_channels = [led_Chanel(pin) for pin in LED_PINS]
        
        self.create_widgets()
    def create_widgets(self):
        self.buttons = []
        for i, led in enumerate(self.led_channels):
            button = tk.Button(self.master, text=f"LED {i+1}", command=lambda idx=i: self.toggle_led(idx))
            button.pack(pady=10)
            self.buttons.append(button)
            
    def toggle_led(self, idx):
        led = self.led_channels[idx]
        led.state = not led.state
        if LED_PINS:
            try:
                GPIO.output(led.pin, GPIO.HIGH if led.state else GPIO.LOW)
            except Exception as e:
                print(f"Error occurred while updating LED {idx+1}: {e}, GPIO functionality may be disabled.")
                
        self.buttons[idx].config(text=f"LED {idx+1} {'ON' if led.state else 'OFF'}")
    
if __name__ == "__main__":
    root = tk.Tk()
    app = LEDControlApp(root)

    
    root.mainloop()
    
    if LED_PINS:
        try:
            GPIO.cleanup()
        except Exception as e:
            print(f"Error during GPIO cleanup: {e}")


