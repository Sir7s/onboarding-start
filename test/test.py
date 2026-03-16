# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb.types import LogicArray


async def await_half_sclk(dut):
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        if (start_time + 100 * 100 * 0.5) < cocotb.utils.get_sim_time(units="ns"):
            break


def ui_in_logicarray(ncs, bit, sclk):
    return LogicArray(f"00000{ncs}{bit}{sclk}")


def uo0_bit(dut):
    return int(dut.uo_out.value) & 0x1


async def wait_for_uo0_rising(dut, timeout_cycles=20000):
    prev = uo0_bit(dut)
    for _ in range(timeout_cycles):
        await ClockCycles(dut.clk, 1)
        cur = uo0_bit(dut)
        if prev == 0 and cur == 1:
            return cocotb.utils.get_sim_time(units="ns")
        prev = cur
    raise AssertionError("Timed out waiting for uo_out[0] rising edge")


async def wait_for_uo0_falling(dut, timeout_cycles=20000):
    prev = uo0_bit(dut)
    for _ in range(timeout_cycles):
        await ClockCycles(dut.clk, 1)
        cur = uo0_bit(dut)
        if prev == 1 and cur == 0:
            return cocotb.utils.get_sim_time(units="ns")
        prev = cur
    raise AssertionError("Timed out waiting for uo_out[0] falling edge")


async def reset_dut(dut):
    dut.ena.value = 1
    dut.uio_in.value = 0

    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)


async def send_spi_transaction(dut, r_w, address, data):
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data

    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")

    first_byte = (int(r_w) << 7) | address

    sclk = 0
    ncs = 0
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)

    for i in range(8):
        bit = (first_byte >> (7 - i)) & 0x1
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)

    for i in range(8):
        bit = (data_int >> (7 - i)) & 0x1
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)

    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)

    return ui_in_logicarray(ncs, bit, sclk)


async def enable_pwm_on_uo0(dut, duty):
    await send_spi_transaction(dut, 1, 0x00, 0x01)
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    await send_spi_transaction(dut, 1, 0x04, duty)
    await ClockCycles(dut.clk, 100)


@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    dut._log.info("Test project behavior")

    dut._log.info("Write transaction, address 0x00, data 0xF0")
    await send_spi_transaction(dut, 1, 0x00, 0xF0)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000)

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    await send_spi_transaction(dut, 1, 0x01, 0xCC)
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    await send_spi_transaction(dut, 1, 0x02, 0xFF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    await send_spi_transaction(dut, 1, 0x04, 0xCF)
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    await send_spi_transaction(dut, 1, 0x04, 0xFF)
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    await send_spi_transaction(dut, 1, 0x04, 0x00)
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    await send_spi_transaction(dut, 1, 0x04, 0x01)
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")


@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start PWM frequency test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)
    await enable_pwm_on_uo0(dut, 0x80)

    await wait_for_uo0_falling(dut)
    t_rise_1 = await wait_for_uo0_rising(dut)
    t_rise_2 = await wait_for_uo0_rising(dut)

    period_ns = t_rise_2 - t_rise_1
    freq_hz = 1e9 / period_ns

    dut._log.info(f"Measured PWM period = {period_ns} ns")
    dut._log.info(f"Measured PWM frequency = {freq_hz:.3f} Hz")

    assert 2970.0 <= freq_hz <= 3030.0, f"PWM frequency out of spec: {freq_hz:.3f} Hz"

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM duty-cycle test")

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    await send_spi_transaction(dut, 1, 0x00, 0x01)
    await send_spi_transaction(dut, 1, 0x02, 0x01)

    dut._log.info("Testing 0% duty")
    await send_spi_transaction(dut, 1, 0x04, 0x00)
    await ClockCycles(dut.clk, 4000)
    assert uo0_bit(dut) == 0, "Expected uo_out[0] low at 0% duty"
    await ClockCycles(dut.clk, 4000)
    assert uo0_bit(dut) == 0, "uo_out[0] should stay low at 0% duty"

    dut._log.info("Testing 100% duty")
    await send_spi_transaction(dut, 1, 0x04, 0xFF)
    await ClockCycles(dut.clk, 4000)
    assert uo0_bit(dut) == 1, "Expected uo_out[0] high at 100% duty"
    await ClockCycles(dut.clk, 4000)
    assert uo0_bit(dut) == 1, "uo_out[0] should stay high at 100% duty"

    dut._log.info("Testing 50% duty")
    await send_spi_transaction(dut, 1, 0x04, 0x80)
    await ClockCycles(dut.clk, 200)

    await wait_for_uo0_falling(dut)
    t_rise = await wait_for_uo0_rising(dut)
    t_fall = await wait_for_uo0_falling(dut)
    t_next_rise = await wait_for_uo0_rising(dut)

    high_time_ns = t_fall - t_rise
    period_ns = t_next_rise - t_rise
    duty_pct = (high_time_ns / period_ns) * 100.0

    dut._log.info(f"Measured high time = {high_time_ns} ns")
    dut._log.info(f"Measured period    = {period_ns} ns")
    dut._log.info(f"Measured duty      = {duty_pct:.3f}%")

    assert 49.0 <= duty_pct <= 51.0, f"PWM duty out of spec: {duty_pct:.3f}%"

    dut._log.info("PWM Duty Cycle test completed successfully")
