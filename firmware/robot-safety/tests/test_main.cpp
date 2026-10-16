#include "test_support.h"

int run_kernel_tests(TestContext& test);
int run_frame_tests(TestContext& test);
int run_integration_tests(TestContext& test);

int main() {
  TestContext test;
  const int kernel_checks = run_kernel_tests(test);
  const int integration_checks = run_integration_tests(test);
  const int frame_checks = run_frame_tests(test);
  std::printf("robot-safety native tests: %d checks passed (kernel=%d frame=%d integration=%d)\n",
              test.checks,
              kernel_checks,
              frame_checks,
              integration_checks);
  return 0;
}
