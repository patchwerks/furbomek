#include <libfreenect2/frame_listener_impl.h>
#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/logger.h>
#include <libfreenect2/packet_pipeline.h>
#include <libfreenect2/registration.h>
#include <turbojpeg.h>
#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

namespace {
volatile std::sig_atomic_t running = 1;
void stop(int) { running = 0; }
using Clock = std::chrono::steady_clock;
constexpr std::uint32_t slots = 512 * 424;
constexpr std::size_t floats_per_slot = 16;

struct CameraSession {
  libfreenect2::Freenect2Device *device;
  bool started = false;
  ~CameraSession() {
    if (started) device->stop();
    device->close();
  }
};

struct FrameLease {
  libfreenect2::SyncMultiFrameListener &listener;
  libfreenect2::FrameMap &frames;
  ~FrameLease() { listener.release(frames); }
};

void publish(const std::filesystem::path &directory, std::uint32_t sequence,
             const std::vector<float> &points) {
  const std::array<std::uint32_t, 4> header{0x32434b46, 1, sequence, slots};
  std::ofstream stream(directory / "next.bin", std::ios::binary);
  stream.exceptions(std::ios::failbit | std::ios::badbit);
  stream.write(reinterpret_cast<const char *>(header.data()), sizeof(header));
  stream.write(reinterpret_cast<const char *>(points.data()),
               static_cast<std::streamsize>(points.size() * sizeof(float)));
  stream.close();
  std::filesystem::rename(directory / "next.bin", directory / "latest.bin");
  const auto snapshot = directory / ("frame-" + std::to_string(sequence % 4) + ".bin");
  std::filesystem::remove(snapshot);
  std::filesystem::create_hard_link(directory / "latest.bin", snapshot);
}

void publish_image(const std::filesystem::path &path, std::uint32_t sequence,
                   const libfreenect2::Frame &frame) {
  std::unique_ptr<void, decltype(&tjDestroy)> compressor(tjInitCompress(), tjDestroy);
  if (!compressor) throw std::runtime_error("JPEG compressor initialization failed.");
  unsigned char *data = nullptr;
  unsigned long size = 0;
  const int result = tjCompress2(compressor.get(), frame.data, static_cast<int>(frame.width), 0,
      static_cast<int>(frame.height), TJPF_BGRX, &data, &size, TJSAMP_444, 92, TJFLAG_FASTDCT);
  std::unique_ptr<unsigned char, decltype(&tjFree)> encoded(data, tjFree);
  if (result != 0) throw std::runtime_error("RGB JPEG encoding failed.");
  const auto pending = path.string() + ".next";
  std::ofstream stream(pending, std::ios::binary);
  stream.exceptions(std::ios::failbit | std::ios::badbit);
  stream.write(reinterpret_cast<const char *>(&sequence), sizeof(sequence));
  stream.write(reinterpret_cast<const char *>(data), static_cast<std::streamsize>(size));
  stream.close();
  std::filesystem::rename(pending, path);
}

int capture(int seconds) {
  const char *configured = std::getenv("FURBOMEK_KINECT_DIR");
  const std::filesystem::path directory = configured ? configured :
      "/dev/shm/furbomek-kinect2-" + std::to_string(getuid());
  umask(0077);
  std::filesystem::create_directories(directory);
  std::filesystem::permissions(directory, std::filesystem::perms::owner_all);
  libfreenect2::setGlobalLogger(libfreenect2::createConsoleLogger(libfreenect2::Logger::Warning));
  libfreenect2::Freenect2 context;
  if (context.enumerateDevices() == 0)
    throw std::runtime_error("No accessible Kinect v2. Check USB3/power and the user device ACL.");
  libfreenect2::OpenGLPacketPipeline pipeline;
  auto *device = context.openDefaultDevice(&pipeline);
  if (!device) throw std::runtime_error("Unable to open Kinect v2.");
  libfreenect2::SyncMultiFrameListener listener(
      libfreenect2::Frame::Color | libfreenect2::Frame::Ir | libfreenect2::Frame::Depth);
  CameraSession session{device};
  device->setColorFrameListener(&listener);
  device->setIrAndDepthFrameListener(&listener);
  if (!device->start()) throw std::runtime_error("Kinect start failed.");
  session.started = true;
  libfreenect2::Registration registration(device->getIrCameraParams(), device->getColorCameraParams());
  libfreenect2::Frame undistorted(512, 424, 4), registered(512, 424, 4);
  std::vector<float> points(slots * floats_per_slot, 0.0f);
  std::vector<int> color_map(slots, -1);
  const auto start = Clock::now();
  auto report = start;
  std::uint32_t sequence = 0;
  std::uint32_t previous_depth = 0;
  std::uint64_t depth_sequence_gaps = 0;
  while (running && (seconds == 0 || Clock::now() - start < std::chrono::seconds(seconds))) {
    libfreenect2::FrameMap frames;
    if (!listener.waitForNewFrame(frames, 2000))
      throw std::runtime_error("No synchronized RGB/IR/depth frame for 2 seconds.");
    FrameLease lease{listener, frames};
    const auto captured = Clock::now();
    const auto *rgb = frames.at(libfreenect2::Frame::Color);
    const auto *depth = frames.at(libfreenect2::Frame::Depth);
    const auto *ir = frames.at(libfreenect2::Frame::Ir);
    if (sequence > 0 && depth->sequence > previous_depth)
      depth_sequence_gaps += depth->sequence - previous_depth - 1;
    previous_depth = depth->sequence;
    registration.apply(rgb, depth, &undistorted, &registered, true, nullptr, color_map.data());
    std::uint32_t valid = 0;
    std::uint32_t colored = 0;
    double ir_sum = 0.0;
    float near_z = 100.0f, far_z = 0.0f;
    std::size_t index = 0;
    for (int row = 0; row < 424; ++row) {
      for (int col = 0; col < 512; ++col, index += floats_per_slot) {
        float x, y, z, packed_color;
        registration.getPointXYZRGB(&undistorted, &registered, row, col, x, y, z, packed_color);
        const auto ir_offset = (static_cast<std::size_t>(row) * 512 + col) * sizeof(float);
        float intensity;
        std::memcpy(&intensity, ir->data + ir_offset, sizeof(float));
        if (std::isfinite(intensity)) ir_sum += intensity;
        std::fill_n(points.begin() + static_cast<std::ptrdiff_t>(index), floats_per_slot, 0.0f);
        points[index + 11] = -100.0f;
        if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) || z < 0.25f || z > 8.0f)
          continue;
        std::array<std::uint8_t, 4> color{};
        std::memcpy(color.data(), &packed_color, sizeof(packed_color));
        points[index] = points[index + 5] = points[index + 10] = 1.0f;
        points[index + 3] = x;
        points[index + 7] = -y;
        points[index + 11] = -z;
        points[index + 12] = color[2] / 255.0f;
        points[index + 13] = color[1] / 255.0f;
        points[index + 14] = color[0] / 255.0f;
        points[index + 15] = 1.0f;
        ++valid;
        if (color[0] || color[1] || color[2]) ++colored;
        near_z = std::min(near_z, z);
        far_z = std::max(far_z, z);
      }
    }
    publish(directory, ++sequence, points);
    const auto stem = "frame-" + std::to_string(sequence % 4);
    publish_image(directory / (stem + ".jpg.bin"), sequence, registered);
    publish_image(directory / (stem + ".optical.bin"), sequence, *rgb);
    std::ofstream map_stream(directory / "next.map", std::ios::binary);
    map_stream.exceptions(std::ios::failbit | std::ios::badbit);
    map_stream.write(reinterpret_cast<const char *>(&sequence), sizeof(sequence));
    map_stream.write(reinterpret_cast<const char *>(color_map.data()),
                     static_cast<std::streamsize>(color_map.size() * sizeof(int)));
    map_stream.close();
    std::filesystem::rename(directory / "next.map", directory / (stem + ".map.bin"));
    const double elapsed = std::chrono::duration<double>(Clock::now() - start).count();
    const auto monotonic_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(captured.time_since_epoch()).count();
    std::ofstream metadata(directory / "next.json");
    metadata.exceptions(std::ios::failbit | std::ios::badbit);
    metadata << "{\"sequence\":" << sequence << ",\"frames\":" << sequence
             << ",\"valid_points\":" << valid << ",\"colored_points\":" << colored
             << ",\"capture_fps\":" << sequence / elapsed << ",\"width\":512,\"height\":424"
             << ",\"rgb_width\":" << rgb->width << ",\"rgb_height\":" << rgb->height
             << ",\"ir_mean\":" << ir_sum / slots << ",\"near_m\":" << near_z
             << ",\"far_m\":" << far_z << ",\"depth_sequence_gaps\":" << depth_sequence_gaps
             << ",\"capture_monotonic_ns\":" << monotonic_ns
             << ",\"frame_file\":\"" << stem << ".bin\",\"image_file\":\"" << stem
             << ".jpg.bin\",\"optical_file\":\"" << stem << ".optical.bin\",\"map_file\":\""
             << stem << ".map.bin\""
             << ",\"depth_provenance\":\"measured\"}\n";
    metadata.close();
    std::filesystem::rename(directory / "next.json", directory / "metadata.json");
    if (Clock::now() - report >= std::chrono::seconds(5)) {
      std::cout << "frames=" << sequence << " fps=" << sequence / elapsed
                << " valid=" << valid << " colored=" << colored
                << " ir_mean=" << ir_sum / slots << " depth_sequence_gaps=" << depth_sequence_gaps << std::endl;
      report = Clock::now();
    }
  }
  std::cout << "capture_complete frames=" << sequence << std::endl;
  return sequence > 0 ? 0 : 1;
}
}

int main(int argc, char **argv) {
  int seconds = 0;
  if (argc == 2 && std::string(argv[1]) == "--help") {
    std::cout << "Usage: furbomek-kinect2 [--seconds N]\n"
              << "Host OpenGL RGB/IR/depth capture; publishes calibrated Godot cloud to FURBOMEK_KINECT_DIR.\n";
    return 0;
  }
  if (argc != 1) {
    if (argc != 3 || std::string(argv[1]) != "--seconds") {
      std::cerr << "Expected --seconds N or --help\n";
      return 2;
    }
    const std::string text(argv[2]);
    const auto result = std::from_chars(text.data(), text.data() + text.size(), seconds);
    if (result.ec != std::errc() || result.ptr != text.data() + text.size() || seconds < 1) {
      std::cerr << "Seconds must be a positive integer\n";
      return 2;
    }
  }
  std::signal(SIGINT, stop);
  std::signal(SIGTERM, stop);
  try { return capture(seconds); }
  catch (const std::exception &error) {
    std::cerr << "capture_failed: " << error.what() << '\n';
    return 1;
  }
}
