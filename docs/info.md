<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

The peripheral index is the number TinyQV will use to select your peripheral.  You will pick a free
slot when raising the pull request against the main TinyQV repository, and can fill this in then.  You
also need to set this value as the PERIPHERAL_NUM in your test script.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

# WatchDog Timer

Author: Niklas Anderson

Peripheral index: nn

## What it does

The watchdog timer (WDT) peripheral provides a mechanism to detect software lockups or system hangs. Once started, it begins counting down from a configured value. If the countdown reaches zero without being "tapped", the WDT asserts an interrupt (user_interrupt) to signal a system fault.

A tap entails writing a specified value (0xABCD) to address 0x3. This is designed to reduce the likelihood of an inadvertent clearing of the interrupt due to corrupt or misbehaving signals. Besides the tap action, only a reset will clear the interrupt.

## Register map

| Address | Name       | Access | Description                                                                 |
|---------|------------|--------|-----------------------------------------------------------------------------|
| 0    | ENABLE     | W      | Write 1 to enable the watchdog, 0 to disable. Does not clear timeout.       |
| 1    | START      | W      | Starts the watchdog (also enables). Has no effect if countdown = 0.         |
| 2    | COUNTDOWN  | R/W    | Sets or reads the countdown value (in clock cycles). 8/16/32-bit writes allowed. |
| 3    | TAP        | W      | Write 0xABCD to reset countdown and clear timeout, only if enabled and started. |
| 4    | STATUS     | R      | Bit 0: enabled, Bit 1: started, Bit 2: timeout_pending, Bit 3: counter active |


## How to test

The WDT is configured and interacted with through memory-mapped registers using byte/half-word/word writes, with countdown resolution based on the system clock (typically 64 MHz). Configuration on system startup requires writing a countdown value to the peripheral, then starting the counter by writing to the start address. The countdown begins immediately, and proceeds until reaching zero or receiving the correct pre-specified value (0xABCD) at the tap address. If the countdown reaches zero before receiving a valid tap, the `user_interrupt` signal is asserted. If a valid tap is recieved, the countdown is restarted and any existing interrupt is de-asserted.

The timer may be disabled by writing a 0 to the enable address. When re-starting the timer by writing to the start address, the counter is reset to the saved countdown value. If no countdown value has been set, the timer will not start.

## External hardware

None
