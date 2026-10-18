#include <Arduino.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>

#include "guard_runtime.h"

constexpr uint8_t kEnableMask = _BV(PK6) | _BV(PK7);
constexpr uint8_t kServoD38Mask = _BV(PD7);
constexpr uint8_t kServoD39Mask = _BV(PG2);

void guard_init3() __attribute__((naked, used, section(".init3")));
void guard_init3() {
  MCUSR = 0;
  wdt_disable();
  PORTK &= static_cast<uint8_t>(~kEnableMask);
  DDRK |= kEnableMask;
  PORTA = 0;
  DDRA = 0xff;
  PORTC = 0;
  DDRC = 0xff;
  PORTD &= static_cast<uint8_t>(~kServoD38Mask);
  DDRD |= kServoD38Mask;
  PORTG &= static_cast<uint8_t>(~kServoD39Mask);
  DDRG |= kServoD39Mask;
}

void serialEvent() {}
void serialEvent1() {}
void serialEvent2() {}
void serialEvent3() {}

ISR(TIMER4_COMPA_vect) { guard_runtime_timer4(); }

void setup() { guard_runtime_setup(); }
void loop() { guard_runtime_loop(); }
