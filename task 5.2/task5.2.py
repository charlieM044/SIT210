

import tkinter as tk

# BCM GPIO numbers that support hardware PWM on Raspberry Pi 4B.
PWM_GPIO_PINS = {12, 13, 18, 19}
LED_PINS = [18, 27, 22]

GPIO_AVAILABLE = False
try:
    import RPi.GPIO as GPIO

    GPIO_AVAILABLE = True
    GPIO.setmode(GPIO.BCM)
except ImportError:
    print("RPi.GPIO library not found. GPIO functionality will be disabled.")


class LedChannel:
    def __init__(self, pin):
        self.pin = pin
        self.state = False
        self.light = 100
        self.is_pwm = pin in PWM_GPIO_PINS
        self.pwm = None


class LEDControlApp:
    def __init__(self, master):
        self.master = master
        self.master.title("LED Control App")
        self.led_channels = [LedChannel(pin) for pin in LED_PINS]
        self.buttons = []
        self.sliders_by_led = {}

        if GPIO_AVAILABLE:
            for led in self.led_channels:
                GPIO.setup(led.pin, GPIO.OUT)
                GPIO.output(led.pin, GPIO.LOW)
                if led.is_pwm:
                    led.pwm = GPIO.PWM(led.pin, 100)
                    led.pwm.start(0)

        self.create_led_buttons()

    def create_led_buttons(self):
        for i, led in enumerate(self.led_channels):
            button = tk.Button(self.master, text=f"LED {i+1}", command=lambda idx=i: self.toggle_led(idx))
            button.pack(pady=10)
            self.buttons.append(button)
            self.buttons[i].config(text=f"LED {i+1} {'ON' if led.state else 'OFF'}")
            if led.is_pwm:
                self.power_slider(i)

    def power_slider(self, idx):
        slider = tk.Scale(
            self.master,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            label=f"LED {idx+1} Brightness",
            command=lambda _val, led_idx=idx: self.update_brightness(led_idx),
        )
        slider.set(self.led_channels[idx].light)
        slider.pack(pady=5)
        self.sliders_by_led[idx] = slider

    def update_brightness(self, idx):
        led = self.led_channels[idx]
        slider = self.sliders_by_led.get(idx)
        if slider is None:
            return

        led.light = slider.get()
        if GPIO_AVAILABLE and led.is_pwm and led.pwm is not None and led.state:
            led.pwm.ChangeDutyCycle(led.light)

        print(f"LED {idx+1} brightness set to {led.light}%")

    def toggle_led(self, idx):
        led = self.led_channels[idx]
        led.state = not led.state

        if GPIO_AVAILABLE:
            try:
                if led.is_pwm and led.pwm is not None:
                    led.pwm.ChangeDutyCycle(led.light if led.state else 0)
                else:
                    GPIO.output(led.pin, GPIO.HIGH if led.state else GPIO.LOW)
            except Exception as e:
                print(f"Error occurred while updating LED {idx+1}: {e}, GPIO functionality may be disabled.")

        self.buttons[idx].config(text=f"LED {idx+1} {'ON' if led.state else 'OFF'}")

    def cleanup(self):
        if not GPIO_AVAILABLE:
            return

        for led in self.led_channels:
            if led.pwm is not None:
                led.pwm.stop()
        GPIO.cleanup()


if __name__ == "__main__":
    root = tk.Tk()
    app = LEDControlApp(root)

    root.mainloop()

    try:
        app.cleanup()
    except Exception as e:
        print(f"Error during GPIO cleanup: {e}")


