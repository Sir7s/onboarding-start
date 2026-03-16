`default_nettype none

module spi_peripheral (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       sclk,
    input  wire       copi,
    input  wire       ncs,
    output reg  [7:0] en_reg_out_7_0,
    output reg  [7:0] en_reg_out_15_8,
    output reg  [7:0] en_reg_pwm_7_0,
    output reg  [7:0] en_reg_pwm_15_8,
    output reg  [7:0] pwm_duty_cycle
);

  // 2-flop synchronizers for external SPI signals
  reg sclk_ff1, sclk_ff2;
  reg copi_ff1, copi_ff2;
  reg ncs_ff1,  ncs_ff2;

  // Previous synchronized values for edge detection
  reg sclk_prev;
  reg ncs_prev;

  // SPI transaction storage
  reg [15:0] spi_shift_reg;
  reg [4:0]  bit_count;

  wire sclk_rise = (sclk_prev == 1'b0) && (sclk_ff2 == 1'b1);
  wire ncs_fall  = (ncs_prev  == 1'b1) && (ncs_ff2  == 1'b0);
  wire ncs_rise  = (ncs_prev  == 1'b0) && (ncs_ff2  == 1'b1);

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      // Reset all control registers
      en_reg_out_7_0  <= 8'h00;
      en_reg_out_15_8 <= 8'h00;
      en_reg_pwm_7_0  <= 8'h00;
      en_reg_pwm_15_8 <= 8'h00;
      pwm_duty_cycle  <= 8'h00;

      // Reset synchronizers/history
      sclk_ff1  <= 1'b0;
      sclk_ff2  <= 1'b0;
      copi_ff1  <= 1'b0;
      copi_ff2  <= 1'b0;
      ncs_ff1   <= 1'b1;
      ncs_ff2   <= 1'b1;
      sclk_prev <= 1'b0;
      ncs_prev  <= 1'b1;

      // Reset SPI capture state
      spi_shift_reg <= 16'h0000;
      bit_count     <= 5'd0;
    end else begin
      // First: synchronize external SPI signals into clk domain
      sclk_ff1 <= sclk;
      sclk_ff2 <= sclk_ff1;

      copi_ff1 <= copi;
      copi_ff2 <= copi_ff1;

      ncs_ff1 <= ncs;
      ncs_ff2 <= ncs_ff1;

      // Start of transaction: nCS falls low
      if (ncs_fall) begin
        spi_shift_reg <= 16'h0000;
        bit_count     <= 5'd0;
      end

      // During transaction: sample COPI on synchronized SCLK rising edge
      if ((ncs_ff2 == 1'b0) && sclk_rise) begin
        if (bit_count < 5'd16) begin
          spi_shift_reg <= {spi_shift_reg[14:0], copi_ff2};
          bit_count     <= bit_count + 5'd1;
        end
      end

      // End of transaction: nCS rises high
      // If exactly 16 bits were captured, decode and write registers
      if (ncs_rise) begin
        if (bit_count == 5'd16) begin
          // spi_shift_reg[15] = R/W bit, 1 means write
          if (spi_shift_reg[15]) begin
            case (spi_shift_reg[14:8]) // 7-bit address
              7'h00: en_reg_out_7_0  <= spi_shift_reg[7:0];
              7'h01: en_reg_out_15_8 <= spi_shift_reg[7:0];
              7'h02: en_reg_pwm_7_0  <= spi_shift_reg[7:0];
              7'h03: en_reg_pwm_15_8 <= spi_shift_reg[7:0];
              7'h04: pwm_duty_cycle  <= spi_shift_reg[7:0];
              default: begin
                // Ignore invalid addresses
              end
            endcase
          end
          // If R/W bit is 0, ignore the transaction
        end
      end

      // Update previous synchronized values for next-cycle edge detection
      sclk_prev <= sclk_ff2;
      ncs_prev  <= ncs_ff2;
    end
  end

endmodule
