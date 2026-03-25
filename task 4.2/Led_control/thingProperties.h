#include <ArduinoIoTCloud.h>
#include <Arduino_ConnectionHandler.h>
#include <Arduino_NetworkConfigurator.h>
#include "configuratorAgents/agents/BLEAgent.h"
#include "configuratorAgents/agents/SerialAgent.h"
void onBathroomChange();
void onClosetChange();
void onLivingRoomChange();

bool Bathroom;
bool Closet;
bool LivingRoom;

KVStore kvStore;
BLEAgentClass BLEAgent;
SerialAgentClass SerialAgent;
WiFiConnectionHandler ArduinoIoTPreferredConnection; 
NetworkConfiguratorClass NetworkConfigurator(ArduinoIoTPreferredConnection);

void initProperties(){
  NetworkConfigurator.addAgent(BLEAgent);
  NetworkConfigurator.addAgent(SerialAgent);
  NetworkConfigurator.setStorage(kvStore);
  // For changing the default reset pin uncomment and set your preferred pin. Use DISABLE_PIN for disabling the reset procedure.
  //NetworkConfigurator.setReconfigurePin(your_pin);
  ArduinoCloud.setConfigurator(NetworkConfigurator);

  ArduinoCloud.addProperty(Bathroom, READWRITE, ON_CHANGE, onBathroomChange);
  ArduinoCloud.addProperty(Closet, READWRITE, ON_CHANGE, onClosetChange);
  ArduinoCloud.addProperty(LivingRoom, READWRITE, ON_CHANGE, onLivingRoomChange);

}
