void setup() {
  Serial.begin(9600);   // To computer
  Serial1.begin(115200);  // To GPS
  while (!Serial);      // Wait for monitor to open
  Serial.println("Starting GPS Bridge...");
}

void loop() {
  // If GPS sends a byte, send it to the computer
  if (Serial1.available()) {
    Serial.write(Serial1.read());
  }
}
