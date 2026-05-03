# Panel

In the panel folder, a 2x2 panel option is available, its size is smaller than 100x100 mm.

# Gerber files

Gerber files can be downloaded in [releases](https://github.com/aroum/cn_tester/releases).

# BOM

| Item                                                      |  Qty | Remarks                  |
| --------------------------------------------------------- | ---: | ------------------------ |
| MCU                                                       |    2 | target and master        |
| [Sockets](https://github.com/joric/nrfmicro/wiki/Sockets) | 12x4 | for MCU                  |
| SMD button 3x4x2mm                                        |    3 | for reset and start test |
| SMD resistor 0603 1-5k                                    |    1 |                          |
| SMD LED 0603                                              |    1 |                          |

[IBOM](https://htmlpreview.github.io/?https://github.com/aroum/PNCATEHO/blob/master/pcb/cn_tester/ibom/ibom.html)

You can use any sockets for the target microcontroller, but if you want to test the microcontroller without soldering I recommend spring pin headers or pogo pins (H032). When using H032 you will need to press them to ensure good contact.

![spring pin](https://private-user-images.githubusercontent.com/852547/405723092-81f82d2c-c411-478a-a34d-f9249b987f54.jpg?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3Nzc3OTA3NzEsIm5iZiI6MTc3Nzc5MDQ3MSwicGF0aCI6Ii84NTI1NDcvNDA1NzIzMDkyLTgxZjgyZDJjLWM0MTEtNDc4YS1hMzRkLWY5MjQ5Yjk4N2Y1NC5qcGc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwNTAzJTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDUwM1QwNjQxMTFaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT02YzVjMjYwZTYzMjE3NDg4OWUwNWE2OTkxNzcyZDhjNjZiNmZlYmY0Y2U3OTIxMTYwZDI5NGEzMmY4NDJhYjU5JlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCZyZXNwb25zZS1jb250ZW50LXR5cGU9aW1hZ2UlMkZqcGVnIn0.y77NcWKNbWCfdUeS-7dsdKGYXl6NTeUTuKWItCsfQM0)

![H032](../pics/H032.png)
![H032](../pics/assembly.jpg)

Thanks to [@ShyPsy](https://github.com/ShyPsy) for choosing and testing suitable pogo pins.
