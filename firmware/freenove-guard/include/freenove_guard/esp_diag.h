#pragma once

#include <stdint.h>

namespace freenove_guard {

class EspPort {
 public:
  virtual uint8_t available() const = 0;
  virtual uint8_t read() = 0;
  virtual bool writable(uint8_t size) const = 0;
  virtual void write(const uint8_t* bytes, uint8_t size) = 0;
};

class EspDiagnostics final {
 public:
  explicit EspDiagnostics(EspPort& port);
  void tick(uint32_t now_ms, uint16_t supply_centivolts);
  bool ready() const;

 private:
  enum class State : uint8_t { InitSend, InitWait, ResetWait, Ready, Prompt, Sent, Failed };
  enum class IpdState : uint8_t { Text, Client, Length, Data, Discard };

  void receive(uint8_t value, uint32_t now_ms, uint16_t supply_centivolts);
  void line(uint32_t now_ms);
  void queue_reply(uint16_t supply_centivolts);
  bool write_text(const char* text);
  void next_init(uint32_t now_ms);

  EspPort& port_;
  State state_;
  IpdState ipd_state_;
  uint8_t init_index_;
  uint32_t deadline_ms_;
  uint8_t prefix_index_;
  uint8_t client_;
  uint16_t payload_length_;
  uint16_t remaining_;
  uint8_t payload_[32];
  uint8_t payload_size_;
  char line_[16];
  uint8_t line_size_;
  uint8_t reply_[5];
  uint8_t reply_size_;
  uint8_t reply_client_;
};

}
