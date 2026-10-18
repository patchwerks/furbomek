#pragma once

#include <Arduino.h>
#include "RF24.h"
#include "FNHRBasic.h"
#include "freenove_guard/clock.h"
#include "freenove_guard/dispatcher.h"

extern RobotAction robot_action;
extern RF24 robot_radio;
extern freenove_guard::Dispatcher dispatcher;
extern uint8_t rf_packet[32];
extern volatile bool terminal_fault;
extern volatile bool motion_updates;
extern volatile uint8_t arm_stage;
extern volatile uint32_t arm_stage_deadline_tick;
extern volatile bool action_pending;
extern volatile uint8_t pending_action;
extern volatile uint8_t pending_vendor[9];
extern volatile uint8_t pending_vendor_size;
extern volatile bool operation_done_pending;
extern volatile bool operation_active;
extern volatile uint32_t operation_deadline_tick;
extern volatile uint32_t timer4_ticks;
extern volatile uint32_t transport_deadline_tick;
extern volatile uint32_t session_deadline_tick;
extern volatile bool timer_deadlines_active;
extern volatile bool guard_service_active;

freenove_guard::ClockSample clock_sample();
bool deadline_reached(uint32_t now, uint32_t deadline);
bool deadline_safe_locked();
void safe_outputs();
void guard_service();
void guard_action();
