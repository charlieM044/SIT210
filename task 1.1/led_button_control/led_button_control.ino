int button = 2;
int led1 = 12;
int led2 = 13;

unsigned long porchStart = 0;
unsigned long hallwayStart = 0;

bool porchOn = false;
bool hallwayOn = false;

void setup() {
  Serial.begin(9600);

  pinMode(button, INPUT);   
  pinMode(led1, OUTPUT);
  pinMode(led2, OUTPUT);

  digitalWrite(led1, LOW);
  digitalWrite(led2, LOW);
}



void lightcontrol()
{
  int buttonState = digitalRead(button);

  if (buttonState == HIGH) 
  {

      if (!porchOn && !hallwayOn) 
      {

        digitalWrite(led1, HIGH);
        digitalWrite(led2, HIGH);

        porchStart = millis();
        hallwayStart = millis();

        porchOn = true;
        hallwayOn = true;
      }
  }
  unsigned long currentTime = millis();
    // porch
  if (porchOn && currentTime - porchStart >= 300) {
    digitalWrite(led1, LOW);
    porchOn = false;
  }
  // hall
  if (hallwayOn && currentTime - hallwayStart >= 600) {
    digitalWrite(led2, LOW);
    hallwayOn = false;
  }
}

void loop() {
  

  lightcontrol();

 
  }



