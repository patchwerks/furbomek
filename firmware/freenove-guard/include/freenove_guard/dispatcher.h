#pragma once

#include "freenove_guard/guard.h"
#include "freenove_guard/manual.h"
#include "freenove_guard/rf_link.h"

namespace freenove_guard {

enum class ReplyRoute : uint8_t { Usb = 0, RadioComputer = 1, RadioManual = 2 };
enum class LinkOwner : uint8_t { None = 0, Computer = 1, Manual = 2 };

class RoutedReplySink {
 public:
  virtual void send(ReplyRoute route, const Frame& frame) = 0;
};

class Dispatcher final : private ReplySink, private FrameObserver {
 public:
  Dispatcher(MotionSink& motion, RoutedReplySink& replies);

  void receive_usb(uint8_t value, uint32_t now_ms);
  void receive_radio(const uint8_t* packet, uint8_t size, uint32_t now_ms);
  void tick(uint32_t now_ms);
  void operation_done();
  void external_fault(uint32_t now_ms);
  Snapshot snapshot(uint32_t now_ms) const;
  LinkOwner owner() const;

 private:
  void send(const Frame& frame) override;
  void on_command(const Command& command) override;
  void on_stop() override;
  void on_frame_error(Result result) override;
  void receive_guard(LinkOwner source, ReplyRoute route, const Frame& frame, uint32_t now_ms);
  void receive_vendor(ReplyRoute route, const Frame& frame, uint32_t now_ms);
  void stop(ReplyRoute route, uint32_t now_ms);

  Guard guard_;
  RoutedReplySink& replies_;
  LinkOwner owner_;
  ReplyRoute owner_route_;
  ReplyRoute route_;
  bool reply_to_ingress_;
  bool manual_operation_;
  FrameDecoder usb_decoder_;
  uint8_t usb_stop_match_;
  uint32_t usb_stop_started_ms_;
  uint32_t ingress_now_ms_;
};

}
