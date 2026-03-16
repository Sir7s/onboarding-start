## How it works

This project is an SPI-controlled PWM peripheral for Tiny Tapeout.

The design receives SPI commands on:
- ui[0] = SCLK
- ui[1] = COPI
- ui[2] = nCS

The SPI peripheral writes five internal control registers:
- 0x00: enable output on uo_out[7:0]
- 0x01: enable output on uio_out[7:0]
- 0x02: enable PWM mode on uo_out[7:0]
- 0x03: enable PWM mode on uio_out[7:0]
- 0x04: PWM duty cycle

These registers drive the provided PWM module, which generates the final 16 output signals.

## How to test

Run the cocotb tests from the `test` folder.

The SPI test writes to the control registers and checks that the outputs behave correctly.

## External hardware

No external hardware is required for simulation.
