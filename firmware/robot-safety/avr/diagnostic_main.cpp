#include <avr/interrupt.h>
#include <avr/io.h>

#include "robot_safety/protocol.h"

namespace {

constexpr uint8_t kRxCapacity = 64;
constexpr uint32_t kCpuHz = 16000000UL;
constexpr uint32_t kBaud = 115200UL;
constexpr uint16_t kTimerCompare = static_cast<uint16_t>(kCpuHz / 64UL / 1000UL - 1UL);

volatile uint8_t rx_buffer[kRxCapacity];
volatile uint8_t rx_head = 0;
volatile uint8_t rx_tail = 0;
volatile uint8_t rx_overflow = 0;
volatile uint8_t rx_hardware_fault = 0;
volatile uint32_t monotonic_ms = 0;
volatile uint8_t reset_cause = 0;

struct DiagnosticSafeSink final : robot_safety::SafetySink {
  void force_safe() override {}
};

struct UartReplySink final : robot_safety::ReplySink {
  bool try_queue(const robot_safety::EncodedFrame& frame) override {
    if (busy_ || frame.size > robot_safety::kMaxFrameLength) {
      return false;
    }
    for (uint8_t index = 0; index < frame.size; ++index) {
      tx_buffer_[index] = frame.bytes[index];
    }
    tx_size_ = frame.size;
    tx_index_ = 0;
    busy_ = true;
    return true;
  }

  void tick() {
    if (!busy_ || (UCSR0A & _BV(UDRE0)) == 0) {
      return;
    }
    UDR0 = tx_buffer_[tx_index_];
    ++tx_index_;
    if (tx_index_ == tx_size_) {
      busy_ = false;
    }
  }

 private:
  uint8_t tx_buffer_[robot_safety::kMaxFrameLength] = {};
  uint8_t tx_size_ = 0;
  uint8_t tx_index_ = 0;
  bool busy_ = false;
};

struct AvrCommitFaultSignal final : robot_safety::CommitFaultSignal {
  uint8_t enter_commit() override {
    const uint8_t saved_status = SREG;
    cli();
    return saved_status;
  }

  void leave_commit(uint8_t saved_status) override { SREG = saved_status; }

  bool fault_pending() const override {
    return rx_overflow != 0 || rx_hardware_fault != 0;
  }
};

DiagnosticSafeSink safe_sink;
UartReplySink reply_sink;
AvrCommitFaultSignal commit_signal;
robot_safety::ProtocolEngine engine(safe_sink, reply_sink, commit_signal);

uint32_t clock_now() {
  const uint8_t saved_status = SREG;
  cli();
  const uint32_t now = monotonic_ms;
  SREG = saved_status;
  return now;
}

bool pop_byte(uint8_t& byte) {
  const uint8_t saved_status = SREG;
  cli();
  if (rx_tail == rx_head) {
    SREG = saved_status;
    return false;
  }
  byte = rx_buffer[rx_tail];
  rx_tail = static_cast<uint8_t>((rx_tail + 1U) & (kRxCapacity - 1U));
  SREG = saved_status;
  return true;
}

void discard_rx() {
  const uint8_t saved_status = SREG;
  cli();
  rx_tail = rx_head;
  SREG = saved_status;
}

void configure_uart0() {
  const uint16_t divisor = static_cast<uint16_t>(kCpuHz / (8UL * kBaud) - 1UL);
  UBRR0H = static_cast<uint8_t>(divisor >> 8U);
  UBRR0L = static_cast<uint8_t>(divisor);
  UCSR0A = _BV(U2X0);
  UCSR0B = _BV(RXEN0) | _BV(TXEN0) | _BV(RXCIE0);
  UCSR0C = _BV(UCSZ01) | _BV(UCSZ00);
}

void configure_timer1() __attribute__((noinline));

void configure_timer1() {
  cli();
  TIMSK1 = 0;
  TCCR1B = 0;
  TCCR1A = 0;
  TCNT1 = 0;
  TIFR1 = _BV(OCF1A);
  OCR1A = kTimerCompare;
  TCCR1B = _BV(WGM12);
  TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);
  TIMSK1 = _BV(OCIE1A);
}

}

ISR(USART0_RX_vect) {
  const uint8_t status = UCSR0A;
  const uint8_t byte = UDR0;
  if ((status & (_BV(FE0) | _BV(DOR0) | _BV(UPE0))) != 0) {
    rx_hardware_fault = 1;
    return;
  }
  const uint8_t next_head = static_cast<uint8_t>((rx_head + 1U) & (kRxCapacity - 1U));
  if (next_head == rx_tail) {
    rx_overflow = 1;
    return;
  }
  rx_buffer[rx_head] = byte;
  rx_head = next_head;
}

ISR(TIMER1_COMPA_vect) {
  ++monotonic_ms;
}

int main() {
  cli();
  reset_cause = MCUSR;
  MCUSR = 0;
  configure_uart0();
  configure_timer1();
  sei();
  for (;;) {
    const uint32_t now = clock_now();
    if (rx_overflow != 0 || rx_hardware_fault != 0) {
      engine.transport_fault(now);
      discard_rx();
    } else {
      engine.tick(now);
      for (uint8_t batch = 0; batch < 8; ++batch) {
        if (rx_overflow != 0 || rx_hardware_fault != 0) {
          engine.transport_fault(clock_now());
          discard_rx();
          break;
        }
        uint8_t byte = 0;
        if (!pop_byte(byte)) {
          break;
        }
        const uint32_t batch_now = clock_now();
        if (rx_overflow != 0 || rx_hardware_fault != 0) {
          engine.transport_fault(batch_now);
          discard_rx();
          break;
        }
        engine.receive(byte, batch_now);
        engine.tick(batch_now);
      }
    }
    reply_sink.tick();
  }
}
