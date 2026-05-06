// #include <TinyGPSPlus.h>

// TinyGPSPlus gps;

// void setup() {
//   Serial.begin(9600);   // try 4800
//   Serial.println("GPS Test Starting...");
// }

// void loop() {
//   while (Serial.available() > 0) {
//     gps.encode(Serial.read());
//   }

//   if (gps.location.isUpdated()) {
//     Serial.print("Latitude : ");
//     Serial.println(gps.location.lat(), 6);
//     Serial.print("Longitude: ");
//     Serial.println(gps.location.lng(), 6);
//     Serial.print("Satellites: ");
//     Serial.println(gps.satellites.value());
//     Serial.println("---");
//   }
// }