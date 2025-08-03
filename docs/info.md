<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

The peripheral index is the number TinyQV will use to select your peripheral.  You will pick a free
slot when raising the pull request against the main TinyQV repository, and can fill this in then.  You
also need to set this value as the PERIPHERAL_NUM in your test script.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

# Your project title

Author: Niklas Anderson

Peripheral index: nn

## What it does

The watchdog timer (WDT) peripheral provides a mechanism to detect software lockups or system hangs. Once started, it begins counting down from a configured value. If the countdown reaches zero without being "tapped", the WDT asserts an interrupt (user_interrupt) to signal a system fault.

## Register map

| Address | Name       | Access | Description                                                                 |
|---------|------------|--------|-----------------------------------------------------------------------------|
| 0    | ENABLE     | W      | Write 1 to enable the watchdog, 0 to disable. Does not clear timeout.       |
| 1    | START      | W      | Starts the watchdog (also enables). Has no effect if countdown = 0.         |
| 2    | COUNTDOWN  | R/W    | Sets or reads the countdown value (in clock cycles). 8/16/32-bit writes allowed. |
| 3    | TAP        | W      | Write 0xABCD to reset countdown and clear timeout, only if enabled and started. |
| 4    | STATUS     | R      | Bit 0: enabled, Bit 1: started, Bit 2: timeout_pending, Bit 3: counter active |


## How to test

Explain how to use your project

## External hardware

None
