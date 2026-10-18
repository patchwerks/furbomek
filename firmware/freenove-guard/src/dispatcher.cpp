#include "freenove_guard/dispatcher.h"

namespace freenove_guard {

Dispatcher::Dispatcher(MotionSink& motion, RoutedReplySink& replies)
    : guard_(motion, *this), replies_(replies), owner_(LinkOwner::None), owner_route_(ReplyRoute::Usb), route_(ReplyRoute::Usb),
      reply_to_ingress_(false), manual_operation_(false), usb_decoder_(), usb_stop_match_(0U), usb_stop_started_ms_(0U), ingress_now_ms_(0U) {}

void Dispatcher::send(const Frame& frame) {
  const bool ingress_supply = reply_to_ingress_ && frame.size > 2U && frame.bytes[2] == 0x35U;
  replies_.send(ingress_supply || owner_ == LinkOwner::None ? route_ : owner_route_, frame);
}

void Dispatcher::receive_usb(uint8_t value, uint32_t now_ms) {
  ingress_now_ms_ = now_ms;
  if (usb_stop_match_ != 0U && static_cast<uint32_t>(now_ms - usb_stop_started_ms_) >= 50U) {
    usb_stop_match_ = 0U;
  }
  if (usb_stop_match_ == 0U && value == kStart) {
    usb_stop_match_ = 1U;
    usb_stop_started_ms_ = now_ms;
  } else if (usb_stop_match_ == 1U && value == kStop) {
    usb_stop_match_ = 2U;
  } else if (usb_stop_match_ == 2U && value == kEnd) {
    usb_stop_match_ = 0U;
    usb_decoder_.reset();
    stop(ReplyRoute::Usb, now_ms);
    return;
  } else if (value == kStart) {
    usb_stop_match_ = 1U;
    usb_stop_started_ms_ = now_ms;
  } else {
    usb_stop_match_ = 0U;
  }
  if (owner_ == LinkOwner::Manual) return;
  usb_decoder_.feed(value, now_ms, *this);
}

void Dispatcher::receive_guard(LinkOwner source, ReplyRoute route, const Frame& frame, uint32_t now_ms) {
  if (valid_readonly_frame(frame, kSupply)) {
    const ReplyRoute previous_route = route_;
    route_ = route;
    reply_to_ingress_ = true;
    for (uint8_t index = 0U; index < frame.size; ++index) guard_.receive(frame.bytes[index], now_ms);
    reply_to_ingress_ = false;
    route_ = previous_route;
    return;
  }
  if (owner_ != LinkOwner::None && (owner_ != source || owner_route_ != route)) {
    const ReplyRoute previous_route = route_;
    route_ = route;
    guard_.reject(Result::WrongState);
    route_ = previous_route;
    return;
  }
  route_ = route;
  const State state_before = guard_.snapshot(now_ms).state;
  for (uint8_t index = 0U; index < frame.size; ++index) guard_.receive(frame.bytes[index], now_ms);
  const Snapshot after = guard_.snapshot(now_ms);
  if (owner_ == LinkOwner::None && frame.size > 2U && frame.bytes[2] == kBegin &&
      guard_.snapshot(now_ms).state == State::Session) { owner_ = source; owner_route_ = route; }
  if (owner_ != LinkOwner::None && state_before != State::Fault && after.state == State::Fault) {
    owner_ = LinkOwner::None;
  }
  if (owner_ == source && after.state == State::Disarmed && frame.size > 2U &&
      frame.bytes[2] == kDisarm) {
    owner_ = LinkOwner::None;
    manual_operation_ = false;
  }
}

void Dispatcher::on_command(const Command& command) {
  Frame frame{};
  if (encode_command(command, frame)) receive_guard(LinkOwner::Computer, ReplyRoute::Usb, frame, ingress_now_ms_);
}

void Dispatcher::on_stop() { stop(ReplyRoute::Usb, ingress_now_ms_); }

void Dispatcher::on_frame_error(Result result) {
  route_ = ReplyRoute::Usb;
  guard_.on_frame_error(result);
  if (guard_.snapshot(ingress_now_ms_).state == State::Fault) owner_ = LinkOwner::None;
}

void Dispatcher::receive_vendor(ReplyRoute route, const Frame& frame, uint32_t now_ms) {
  VendorAction action{};
  if (owner_ != LinkOwner::Manual || !decode_vendor_action(frame.bytes, frame.size, action)) return;
  route_ = route;
  manual_operation_ = guard_.receive_vendor(action, now_ms) && !vendor_heartbeat(action);
}

void Dispatcher::stop(ReplyRoute route, uint32_t now_ms) {
  route_ = route;
  guard_.receive(kStart, now_ms);
  guard_.receive(kStop, now_ms);
  guard_.receive(kEnd, now_ms);
  owner_ = LinkOwner::None;
  manual_operation_ = false;
}

void Dispatcher::receive_radio(const uint8_t* packet, uint8_t size, uint32_t now_ms) {
  uint8_t source = 0U;
  Frame frame{};
  if (!unwrap_rf(packet, size, source, frame)) return;
  const ReplyRoute route = source == kRfManualSource ? ReplyRoute::RadioManual : ReplyRoute::RadioComputer;
  if (frame.size == 3U && frame.bytes[0] == kStart && frame.bytes[1] == kStop && frame.bytes[2] == kEnd) {
    stop(route, now_ms);
    return;
  }
  if (source == kRfComputerSource) receive_guard(LinkOwner::Computer, route, frame, now_ms);
  else if (source == kRfManualSource) {
    VendorAction action{};
    if (decode_vendor_action(frame.bytes, frame.size, action)) receive_vendor(route, frame, now_ms);
    else receive_guard(LinkOwner::Manual, route, frame, now_ms);
  }
}

void Dispatcher::tick(uint32_t now_ms) {
  usb_decoder_.tick(now_ms, *this);
  guard_.tick(now_ms);
  if (guard_.snapshot(now_ms).state == State::Fault) owner_ = LinkOwner::None;
}

void Dispatcher::operation_done() { guard_.operation_done(!manual_operation_); manual_operation_ = false; }
void Dispatcher::external_fault(uint32_t now_ms) { guard_.external_fault(now_ms); owner_ = LinkOwner::None; }
Snapshot Dispatcher::snapshot(uint32_t now_ms) const { return guard_.snapshot(now_ms); }
LinkOwner Dispatcher::owner() const { return owner_; }

}
