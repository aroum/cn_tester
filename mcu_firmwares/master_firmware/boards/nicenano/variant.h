#ifndef _VARIANT_NICENANO_
#define _VARIANT_NICENANO_

/** Led state needed **/
#define LED_STATE_ON 1
#define LED_STATE_OFF 0

/** Master clock frequency */
#define VARIANT_MCK       (64000000ul)
  
#define USE_LFXO      // Board uses 32khz crystal for LF (on the nicenano/supermini)
//#define USE_LFRC    // Board uses RC for LF

#include "WVariant.h"

#ifdef __cplusplus
extern "C"
{
#endif // __cplusplus

#define PINS_COUNT 48
#define PIN_SERIAL1_TX  6   // P0.00
#define PIN_SERIAL1_RX  8   // P0.01
#define P0_02  2   // P0.02
#define P0_03  3   // P0.03
#define P0_04  4   // P0.04
#define P0_05  5   // P0.05
#define P0_06  6   // P0.06
#define P0_07  7   // P0.07
#define P0_08  8   // P0.08
#define P0_09  9   // P0.09
#define P0_10  10  // P0.10
#define P0_11  11  // P0.11
#define P0_12  12  // P0.12
#define P0_13  13  // P0.13
#define P0_14  14  // P0.14
#define P0_15  15  // P0.15
#define P0_16  16  // P0.16
#define P0_17  17  // P0.17
#define P0_18  18  // P0.18
#define P0_19  19  // P0.19
#define P0_20  20  // P0.20
#define P0_21  21  // P0.21
#define P0_22  22  // P0.22
#define P0_23  23  // P0.23
#define P0_24  24  // P0.24
#define P0_25  25  // P0.25
#define P0_26  26  // P0.26
#define P0_27  27  // P0.27
#define P0_28  28  // P0.28
#define P0_29  29  // P0.29
#define P0_30  30  // P0.30
#define P0_31  31  // P0.31
#define P1_00  32  // P1.00
#define P1_01  33  // P1.01
#define P1_02  34  // P1.02
#define P1_03  35  // P1.03
#define P1_04  36  // P1.04 (SDA) (SPECIFY &Wire)
#define P1_05  37  // P1.05
#define P1_06  38  // P1.06 (SCL) (SPECIFY &Wire)
#define P1_07  39  // P1.07 (ss) (uncomment line 90 to use)
#define P1_08  40  // P1.08
#define P1_09  41  // P1.09
#define P1_10  42  // P1.10
#define P1_11  43  // P1.11 (SCK)
#define P1_12  44  // P1.12
#define P1_13  45  // P1.13 (MOSI)
#define P1_14  46  // P1.14
#define P1_15  47  // P1.15 (MISO)

#ifndef LED_BUILTIN
#define LED_BUILTIN P0_15
#endif

#ifndef LED_BLUE
#define LED_BLUE P1_14 //added so bluefruit compiles. not in use, 
#endif                  //if you do wanna use it, change the P1_14 to whatever you want

#define WIRE_INTERFACES_COUNT 1

#define PIN_WIRE_SDA 36
#define PIN_WIRE_SCL 38

#define SPI_INTERFACES_COUNT 1

#define PIN_SPI_MISO 47
#define PIN_SPI_MOSI 45
#define PIN_SPI_SCK 43

//static const uint8_t SS   = 39 ;
static const uint8_t MOSI = PIN_SPI_MOSI ;
static const uint8_t MISO = PIN_SPI_MISO ;
static const uint8_t SCK  = PIN_SPI_SCK ;

#ifdef __cplusplus
}
#endif

/*----------------------------------------------------------------------------
 *        Arduino objects - C++ only
 *----------------------------------------------------------------------------*/

#endif
