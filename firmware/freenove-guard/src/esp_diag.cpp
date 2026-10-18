#include "freenove_guard/esp_diag.h"

#include <string.h>

namespace freenove_guard {
namespace {
const char* const kInit[] = {"AT+RST\r\n", "AT+CWMODE_CUR=2\r\n", "AT+CIPMUX=1\r\n",
                             "AT+CIPSERVER=1,65535\r\n", "AT+CIPSTO=0\r\n",
                             "AT+CWSAP_CUR=\"Freenove Hexapod Robot\",\"Freenove\",1,4\r\n"};
const char kIpd[] = "+IPD,";
bool contains(const char* text, const char* token) { return strstr(text, token) != nullptr; }
}

EspDiagnostics::EspDiagnostics(EspPort& port)
    : port_(port), state_(State::InitSend), ipd_state_(IpdState::Text), init_index_(0U), deadline_ms_(0U),
      prefix_index_(0U), client_(0U), payload_length_(0U), remaining_(0U), payload_{}, payload_size_(0U),
      line_{}, line_size_(0U), reply_{}, reply_size_(0U), reply_client_(0U) {}

bool EspDiagnostics::ready() const { return state_ == State::Ready; }

bool EspDiagnostics::write_text(const char* text) {
  const uint8_t size = static_cast<uint8_t>(strlen(text));
  if (!port_.writable(size)) return false;
  port_.write(reinterpret_cast<const uint8_t*>(text), size);
  return true;
}

void EspDiagnostics::next_init(uint32_t now_ms) {
  ++init_index_;
  state_ = init_index_ == sizeof(kInit) / sizeof(kInit[0]) ? State::Ready : State::InitSend;
  deadline_ms_ = now_ms + 1000U;
}

void EspDiagnostics::queue_reply(uint16_t supply) {
  if (reply_size_ != 0U) return;
  if (payload_size_ == 3U && payload_[0] == 0x80U && payload_[1] == 0U && payload_[2] == 0x81U) {
    reply_[0] = 0x80U; reply_[1] = 1U; reply_[2] = 0x81U; reply_size_ = 3U; reply_client_ = client_;
  } else if (payload_size_ == 3U && payload_[0] == 0x80U && payload_[1] == 0x0aU && payload_[2] == 0x81U) {
    reply_[0] = 0x80U; reply_[1] = 0x0bU; reply_[2] = static_cast<uint8_t>(supply / 128U);
    reply_[3] = static_cast<uint8_t>(supply % 128U); reply_[4] = 0x81U; reply_size_ = 5U; reply_client_ = client_;
  }
}

void EspDiagnostics::line(uint32_t now_ms) {
  line_[line_size_] = '\0';
  if (state_ == State::InitWait && contains(line_, "OK")) {
    if (init_index_ == 0U) {
      state_ = State::ResetWait;
      deadline_ms_ = now_ms + 750U;
    } else {
      next_init(now_ms);
    }
  } else if (state_ == State::Prompt && contains(line_, "ERROR")) {
    reply_size_ = 0U; state_ = State::Ready;
  } else if (state_ == State::Sent && (contains(line_, "SEND OK") || contains(line_, "ERROR"))) {
    reply_size_ = 0U; state_ = State::Ready;
  }
  line_size_ = 0U;
}

void EspDiagnostics::receive(uint8_t value, uint32_t now_ms, uint16_t supply) {
  if (ipd_state_ == IpdState::Client) {
    if (value >= '0' && value <= '9') client_ = static_cast<uint8_t>(client_ * 10U + value - '0');
    else if (value == ',') ipd_state_ = IpdState::Length;
    else ipd_state_ = IpdState::Text;
    return;
  }
  if (ipd_state_ == IpdState::Length) {
    if (value >= '0' && value <= '9') payload_length_ = static_cast<uint16_t>(payload_length_ * 10U + value - '0');
    else if (value == ':') { remaining_ = payload_length_; payload_size_ = 0U; ipd_state_ = remaining_ == 0U ? IpdState::Text : (remaining_ <= sizeof(payload_) ? IpdState::Data : IpdState::Discard); }
    else ipd_state_ = IpdState::Text;
    return;
  }
  if (ipd_state_ == IpdState::Data || ipd_state_ == IpdState::Discard) {
    if (ipd_state_ == IpdState::Data) payload_[payload_size_++] = value;
    if (--remaining_ == 0U) { if (state_ == State::Ready) queue_reply(supply); ipd_state_ = IpdState::Text; }
    return;
  }
  if (state_ == State::Prompt && value == '>') { if (port_.writable(reply_size_)) { port_.write(reply_, reply_size_); state_ = State::Sent; deadline_ms_ = now_ms + 500U; } return; }
  if (value == static_cast<uint8_t>(kIpd[prefix_index_])) {
    if (++prefix_index_ == sizeof(kIpd) - 1U) { ipd_state_ = IpdState::Client; prefix_index_ = 0U; client_ = 0U; payload_length_ = 0U; line_size_ = 0U; }
  } else prefix_index_ = value == '+' ? 1U : 0U;
  if (line_size_ + 1U < sizeof(line_)) line_[line_size_++] = static_cast<char>(value);
  if (value == '\n') line(now_ms);
}

void EspDiagnostics::tick(uint32_t now_ms, uint16_t supply) {
  for (uint8_t count = 0U; count < 32U && port_.available() > 0U; ++count) receive(port_.read(), now_ms, supply);
  if (state_ == State::InitSend && write_text(kInit[init_index_])) { state_ = State::InitWait; deadline_ms_ = now_ms + 1200U; }
  else if (state_ == State::ResetWait && static_cast<uint32_t>(now_ms - deadline_ms_) < 0x80000000UL) next_init(now_ms);
  else if ((state_ == State::InitWait || state_ == State::Prompt || state_ == State::Sent) && static_cast<uint32_t>(now_ms - deadline_ms_) < 0x80000000UL) state_ = State::Failed;
  if (state_ == State::Ready && reply_size_ != 0U) {
    char command[] = "AT+CIPSEND=0,0\r\n";
    command[11] = static_cast<char>('0' + reply_client_);
    command[13] = static_cast<char>('0' + reply_size_);
    if (write_text(command)) { state_ = State::Prompt; deadline_ms_ = now_ms + 500U; }
  }
}

}
