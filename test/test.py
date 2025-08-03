# SPDX-FileCopyrightText: © 2025 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from tqv import TinyQV

# When submitting your design, change this to the peripheral number
# in peripherals.v.  e.g. if your design is i_user_peri05, set this to 5.
# The peripheral number is not used by the test harness.
PERIPHERAL_NUM = 0
CLK_PERIOD_NS = 100  # 10 MHz test clock (instead of 64 MHz)

# The TAP magic number is used to reset the watchdog timer and prevent firing of an interrupt.
# It is defined in the peripheral's source code.
TAP_MAGIC = 0xABCD
TAP_INVALID = 0xFFFF
WDT_ADDR = {
    "enable":     0,  # Write 1 to enable, 0 to disable (also clears interrupt)
    "start":      1,  # Write 1 to start timer (implicitly enables)
    "countdown":  2,  # R/W 8/16/32-bit countdown value
    "tap":        3,  # Write 0xABCD to reset countdown and clear interrupt
}

@cocotb.test(skip=True)
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Interact with your design's registers through this TinyQV class.
    # This will allow the same test to be run when your design is integrated
    # with TinyQV - the implementation of this class will be replaces with a
    # different version that uses Risc-V instructions instead of the SPI test
    # harness interface to read and write the registers.
    tqv = TinyQV(dut, PERIPHERAL_NUM)

    # Reset
    await tqv.reset()

    dut._log.info("Test project behavior")

    # Test register write and read back
    await tqv.write_word_reg(0, 0x82345678)
    assert await tqv.read_byte_reg(0) == 0x78
    assert await tqv.read_hword_reg(0) == 0x5678
    assert await tqv.read_word_reg(0) == 0x82345678

    # Set an input value, in the example this will be added to the register value
    dut.ui_in.value = 30

    # Wait for two clock cycles to see the output values, because ui_in is synchronized over two clocks,
    # and a further clock is required for the output to propagate.
    await ClockCycles(dut.clk, 3)

    # The following assersion is just an example of how to check the output values.
    # Change it to match the actual expected output of your module:
    assert dut.uo_out.value == 0x96

    # Input value should be read back from register 1
    assert await tqv.read_byte_reg(4) == 30

    # Zero should be read back from register 2
    assert await tqv.read_word_reg(8) == 0

    # A second write should work
    await tqv.write_word_reg(0, 40)
    assert dut.uo_out.value == 70

    # Test the interrupt, generated when ui_in[6] goes high
    dut.ui_in[6].value = 1
    await ClockCycles(dut.clk, 1)
    dut.ui_in[6].value = 0

    # Interrupt asserted
    await ClockCycles(dut.clk, 3)
    assert await tqv.is_interrupt_asserted()

    # Interrupt doesn't clear
    await ClockCycles(dut.clk, 10)
    assert await tqv.is_interrupt_asserted()

    # Write bottom bit of address 8 high to clear
    await tqv.write_byte_reg(8, 1)
    assert not await tqv.is_interrupt_asserted()


@cocotb.test()
async def test_watchdog_interrupt_on_timeout(dut):
    """Basic test to check that the watchdog timer asserts an interrupt on timeout."""
    dut._log.info("Starting WDT timeout test")

    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 10  # enough to count down in test environment

    # Set countdown value
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)

    # Start the watchdog
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait for timeout (countdown_ticks + a few cycles)
    await ClockCycles(dut.clk, countdown_ticks + 3)

    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"


@cocotb.test()
async def test_watchdog_tap_prevents_timeout(dut):
    """Basic test to check that tapping the watchdog prevents an interrupt."""
    dut._log.info("Starting WDT tap prevents interrupt test")

    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 100

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait until we have confirmed an interrupt has been asserted
    await ClockCycles(dut.clk, countdown_ticks)
    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    # Tap the watchdog to reset countdown and clear interrupt
    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_MAGIC)

    # Wait again a few cycles and then check that the interrupt is not asserted
    await ClockCycles(dut.clk, countdown_ticks // 4)

    assert not await tqv.is_interrupt_asserted(), "Interrupt incorrectly asserted after tap"


@cocotb.test()
async def test_enable_does_not_clear_timeout(dut):
    """Writing 0 to enable register should NOT clear a pending timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 10

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait until we have confirmed an interrupt has been asserted
    await ClockCycles(dut.clk, countdown_ticks)
    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    await tqv.write_word_reg(WDT_ADDR["enable"], 0)

    assert await tqv.is_interrupt_asserted(), "Interrupt cleared by enable write of zero"


@cocotb.test()
async def test_multiple_valid_taps_prevent_interrupt(dut):
    """Multiple correct taps should keep reloading the countdown and prevent timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 100

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Tap the watchdog multiple times within countdown period.
    # The total cycles exceeds countdown_ticks, but the taps should prevent the interrupt.
    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_MAGIC)
    await ClockCycles(dut.clk, countdown_ticks // 2)

    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_MAGIC)
    await ClockCycles(dut.clk, countdown_ticks // 2)

    assert not await tqv.is_interrupt_asserted(), "Interrupt incorrectly asserted after valid taps"


@cocotb.test()
async def test_tap_with_wrong_value_ignored(dut):
    """Writing incorrect value to tap address should have no effect (timeout occurs)."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 100

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait until we have confirmed an interrupt has been asserted
    await ClockCycles(dut.clk, countdown_ticks)
    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    # Tap the watchdog with valid number, should *not* reset countdown and clear interrupt
    await tqv.write_word_reg(WDT_ADDR["tap"], TAP_INVALID)

    # Wait again a few cycles and then check that the interrupt is still asserted
    await ClockCycles(dut.clk, countdown_ticks // 4)

    assert await tqv.is_interrupt_asserted(), "Interrupt cleared by invalid tap"


@cocotb.test()
async def test_start_does_not_clear_interrupt(dut):
    """Writes to 'start' should not clear timeout."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 50

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    await ClockCycles(dut.clk, countdown_ticks)

    assert await tqv.is_interrupt_asserted(), "Interrupt not asserted on timeout"

    # Writing to start should reload the counter, but not clear any existing interrupt
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    assert await tqv.is_interrupt_asserted(), "Write to start incorrectly cleared interrupt"


@cocotb.test()
async def test_repeated_start_reloads_countdown(dut):
    """Multiple writes to 'start' should reload countdown."""
    clock = Clock(dut.clk, CLK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    tqv = TinyQV(dut, PERIPHERAL_NUM)
    await tqv.reset()

    countdown_ticks = 100

    # Set countdown
    await tqv.write_word_reg(WDT_ADDR["countdown"], countdown_ticks)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    # Wait half the countdown, write to start, wait the other half and check interrupt not asserted
    await ClockCycles(dut.clk, countdown_ticks // 2)
    await tqv.write_word_reg(WDT_ADDR["start"], 1)

    await ClockCycles(dut.clk, countdown_ticks // 2)

    assert not await tqv.is_interrupt_asserted(), "Write to start did not reload countdown"


@cocotb.test(skip=True)
async def test_disable_does_not_clear_interrupt(dut):
    """Disabling watchdog after timeout should NOT clear interrupt."""
    pass


@cocotb.test(skip=True)
async def test_partial_write_8bit_zeros_upper_bits(dut):
    """8-bit write to countdown should zero upper 24 bits."""
    pass


@cocotb.test(skip=True)
async def test_partial_write_16bit_zeros_upper_bits(dut):
    """16-bit write to countdown should zero upper 16 bits."""
    pass


@cocotb.test(skip=True)
async def test_countdown_value_readback(dut):
    """Read from countdown address should return last written value."""
    pass


@cocotb.test(skip=True)
async def test_start_without_countdown_value(dut):
    """Starting the watchdog without setting countdown should not start the timer."""
    pass


@cocotb.test(skip=True)
async def test_tap_after_timeout_reloads_and_clears(dut):
    """Tapping after a timeout should reload countdown and clear interrupt."""
    pass


@cocotb.test(skip=True)
async def test_disable_before_start_has_no_effect(dut):
    """Disabling before the watchdog is started should not trigger an interrupt."""
    pass


@cocotb.test(skip=True)
async def test_status_after_start(dut):
    """Status register reflects enabled=1, started=1, counter!=0 before timeout."""
    pass


@cocotb.test(skip=True)
async def test_status_after_timeout(dut):
    """Status register reflects timeout_pending=1 after timer expiry."""
    pass
