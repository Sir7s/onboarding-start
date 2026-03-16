/*
 * Copyright (c) 2024 Boyu Qiu
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_uwasic_onboarding_boyu_qiu (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path
    input  wire       ena,      // always 1 when powered
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // Make all bidirectional IOs act as outputs
  assign uio_oe = 8'hFF;

  // SPI-controlled registers
  wire [7:0] en_reg_out_7_0;
  wire [7:0] en_reg_out_15_8;
  wire [7:0] en_reg_pwm_7_0;
  wire [7:0] en_reg_pwm_15_8;
  wire [7:0] pwm_duty_cycle;

  spi_peripheral spi_peripheral_inst (
      .clk(clk),
      .rst_n(rst_n),
      .sclk(ui_in[0]),
      .copi(ui_in[1]),
      .ncs(ui_in[2]),
      .en_reg_out_7_0(en_reg_out_7_0),
      .en_reg_out_15_8(en_reg_out_15_8),
      .en_reg_pwm_7_0(en_reg_pwm_7_0),
      .en_reg_pwm_15_8(en_reg_pwm_15_8),
      .pwm_duty_cycle(pwm_duty_cycle)
  );

  pwm_peripheral pwm_peripheral_inst (
      .clk(clk),
      .rst_n(rst_n),
      .en_reg_out_7_0(en_reg_out_7_0),
      .en_reg_out_15_8(en_reg_out_15_8),
      .en_reg_pwm_7_0(en_reg_pwm_7_0),
      .en_reg_pwm_15_8(en_reg_pwm_15_8),
      .pwm_duty_cycle(pwm_duty_cycle),
      .out({uio_out, uo_out})
  );

  // List currently unused inputs to avoid warnings
  wire _unused = &{ena, ui_in[7:3], uio_in, 1'b0};

endmodule
