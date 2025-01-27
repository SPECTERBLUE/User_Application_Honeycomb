/*********************************************************
  UTILITY FUNCTIONS
*********************************************************/

/**
 * Parses an 8-byte DevEUI array into a hex string.
 * Example: [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
 *          -> "1122334455667788"
 */
function parseDevEUI(devEUIBytes) {
  if (devEUIBytes.length !== 8) {
    throw new Error("DevEUI must be 8 bytes.");
  }
  return Array.from(devEUIBytes)
    .map(b => b.toString(16).padStart(2, "0"))
    .join("")
    .toUpperCase();
}

/**
 * Parses a 4-byte timestamp (big-endian) into a JS number (uint32).
 * We assume it's an epoch time in seconds, so it can represent dates 
 * up to early 2106 (2^32 - 1).
 */
function parseTimestamp(tsBytes) {
  if (tsBytes.length !== 4) {
    throw new Error("Timestamp must be 4 bytes.");
  }
  // Big-endian parse
  const ts = (tsBytes[0] << 24) | (tsBytes[1] << 16) | (tsBytes[2] << 8) | tsBytes[3];
  // ts is now a 32-bit unsigned integer range. In JS, it becomes a normal Number.
  // Usually we interpret this as "seconds since 1970-01-01T00:00:00Z".
  return ts >>> 0;  // ensure non-negative, as JavaScript bitwise ops can sign-extend
}

/**
 * Parses 2 bytes as a signed 16-bit integer (big-endian).
 * Example: [0x01, 0xF4] -> decimal 500
 */
function parseInt16(twoBytes) {
  if (twoBytes.length !== 2) {
    throw new Error("Expected 2 bytes for a 16-bit value.");
  }
  let value = (twoBytes[0] << 8) | (twoBytes[1] & 0xff);
  if (value & 0x8000) value -= 0x10000; // sign extension for negative
  return value;
}

/**
 * Throws an error if a sensor value is out of a "reasonable" range.
 * Adjust min/max to suit your actual sensor specs.
 */
function validateRange(value, min, max, fieldName) {
  if (value < min || value > max) {
    throw new Error(`${fieldName} out of range: ${value}`);
  }
}

/*********************************************************
  1) TEMPERATURE DECODER
*********************************************************/
/**
 * Format (14 bytes total):
 *   [0..7]   DevEUI (8 bytes)
 *   [8..11]  Timestamp (4 bytes, epoch seconds, big-endian)
 *   [12..13] Temperature (2 bytes, signed 16-bit)
 * Example scaling: 1 LSB = 0.01 °C
 */
class TemperatureDataDecoder {
  decode(bytes) {
    const MIN_LENGTH = 14;
    if (bytes.length < MIN_LENGTH) {
      throw new Error(`Temperature packet must be at least ${MIN_LENGTH} bytes`);
    }

    const devEUI = parseDevEUI(bytes.slice(0, 8));
    const timestamp = parseTimestamp(bytes.slice(8, 12));

    const rawTemp = parseInt16(bytes.slice(12, 14));
    // Example: if firmware sends temperature in hundredths of °C
    const temperature = rawTemp / 100;

    // Optional range check: -50..125 °C
    validateRange(temperature, -50, 125, "Temperature");

    return [
      {
        bn: `urn:dev:${devEUI}:`,
        bt: timestamp, // epoch time in seconds
        n: "temperature",
        u: "Cel",
        v: temperature
      }
    ];
  }
}

/*********************************************************
  2) HUMIDITY DECODER
*********************************************************/
/**
 * Format (14 bytes total):
 *   [0..7]   DevEUI
 *   [8..11]  Timestamp (epoch)
 *   [12..13] Humidity (2 bytes, signed 16-bit)
 * Example scaling: 1 LSB = 0.01 %RH
 */
class HumidityDataDecoder {
  decode(bytes) {
    const MIN_LENGTH = 14;
    if (bytes.length < MIN_LENGTH) {
      throw new Error(`Humidity packet must be at least ${MIN_LENGTH} bytes`);
    }

    const devEUI = parseDevEUI(bytes.slice(0, 8));
    const timestamp = parseTimestamp(bytes.slice(8, 12));

    const rawHum = parseInt16(bytes.slice(12, 14));
    // Example: if firmware sends humidity in hundredths of %RH
    const humidity = rawHum / 100;

    // Range check: 0..100 %RH
    validateRange(humidity, 0, 100, "Humidity");

    return [
      {
        bn: `urn:dev:${devEUI}:`,
        bt: timestamp,
        n: "humidity",
        u: "%RH",
        v: humidity
      }
    ];
  }
}

/*********************************************************
  3) IMU DECODER (PITCH, ROLL, YAW)
*********************************************************/
/**
 * Format (18 bytes total):
 *   [0..7]   DevEUI
 *   [8..11]  Timestamp (epoch)
 *   [12..13] Pitch (2 bytes)
 *   [14..15] Roll  (2 bytes)
 *   [16..17] Yaw   (2 bytes)
 * Example scaling: 1 LSB = 0.01 deg
 */
class IMUDataDecoder {
  decode(bytes) {
    const MIN_LENGTH = 18;
    if (bytes.length < MIN_LENGTH) {
      throw new Error(`IMU packet must be at least ${MIN_LENGTH} bytes`);
    }

    const devEUI = parseDevEUI(bytes.slice(0, 8));
    const timestamp = parseTimestamp(bytes.slice(8, 12));

    const rawPitch = parseInt16(bytes.slice(12, 14));
    const rawRoll  = parseInt16(bytes.slice(14, 16));
    const rawYaw   = parseInt16(bytes.slice(16, 18));

    const pitch = rawPitch / 100;
    const roll  = rawRoll  / 100;
    const yaw   = rawYaw   / 100;

    // Optional range checks
    validateRange(pitch, -180, 180, "Pitch");
    validateRange(roll,  -180, 180, "Roll");
    validateRange(yaw,   -180, 180, "Yaw");

    return [
      {
        bn: `urn:dev:${devEUI}:`,
        bt: timestamp,
        n: "pitch",
        u: "deg",
        v: pitch
      },
      {
        bn: `urn:dev:${devEUI}:`,
        bt: timestamp,
        n: "roll",
        u: "deg",
        v: roll
      },
      {
        bn: `urn:dev:${devEUI}:`,
        bt: timestamp,
        n: "yaw",
        u: "deg",
        v: yaw
      }
    ];
  }
}

/*********************************************************
  4) VIBRATION DECODER
*********************************************************/
/**
 * Format (14 bytes total):
 *   [0..7]   DevEUI
 *   [8..11]  Timestamp (epoch)
 *   [12..13] Vibration reading (2 bytes)
 * Example: if 1 LSB = 1 mg, we convert mg -> g by /1000
 */
class VibrationDataDecoder {
  decode(bytes) {
    const MIN_LENGTH = 14;
    if (bytes.length < MIN_LENGTH) {
      throw new Error(`Vibration packet must be at least ${MIN_LENGTH} bytes`);
    }

    const devEUI = parseDevEUI(bytes.slice(0, 8));
    const timestamp = parseTimestamp(bytes.slice(8, 12));

    const rawVib = parseInt16(bytes.slice(12, 14));
    const vibration = rawVib / 1000; // mg -> g

    // Optional range check: 0..16 g
    validateRange(vibration, 0, 16, "Vibration");

    return [
      {
        bn: `urn:dev:${devEUI}:`,
        bt: timestamp,
        n: "vibration",
        u: "g",
        v: vibration
      }
    ];
  }
}

/*********************************************************
  5) DISTANCE DECODER
*********************************************************/
/**
 * Format (14 bytes total):
 *   [0..7]   DevEUI
 *   [8..11]  Timestamp (epoch)
 *   [12..13] Distance (2 bytes)
 * Example: if 1 LSB = 1 cm, we convert cm -> m by /100
 */
class DistanceDataDecoder {
  decode(bytes) {
    const MIN_LENGTH = 14;
    if (bytes.length < MIN_LENGTH) {
      throw new Error(`Distance packet must be at least ${MIN_LENGTH} bytes`);
    }

    const devEUI = parseDevEUI(bytes.slice(0, 8));
    const timestamp = parseTimestamp(bytes.slice(8, 12));

    const rawDist = parseInt16(bytes.slice(12, 14));
    const distance = rawDist / 100; // cm -> m

    // Optional range check: e.g., 0..100 m
    validateRange(distance, 0, 100, "Distance");

    return [
      {
        bn: `urn:dev:${devEUI}:`,
        bt: timestamp,
        n: "distance",
        u: "m",
        v: distance
      }
    ];
  }
}

/*********************************************************
  COMBINED Decode FUNCTION 
  (For ChirpStack or general usage)
*********************************************************/
function Decode(fPort, bytes) {
  try {
    // Instantiate decoders
    const tempDecoder = new TemperatureDataDecoder();
    const humDecoder  = new HumidityDataDecoder();
    const imuDecoder  = new IMUDataDecoder();
    const vibDecoder  = new VibrationDataDecoder();
    const distDecoder = new DistanceDataDecoder();

    switch (fPort) {
      case 10:
        return tempDecoder.decode(bytes);
      case 11:
        return humDecoder.decode(bytes);
      case 12:
        return imuDecoder.decode(bytes);
      case 13:
        return vibDecoder.decode(bytes);
      case 14:
        return distDecoder.decode(bytes);
      default:
        return { error: "Unknown fPort: " + fPort };
    }
  } catch (err) {
    return { error: err.message };
  }
}

/*********************************************************
  EXAMPLE USAGE DEMO 
  (Uncomment and run in Node.js or browser console)
*********************************************************/
// function exampleUsage() {
//   // Example Temperature packet: 14 bytes
//   // DevEUI:    11 22 33 44 55 66 77 88 (8 bytes)
//   // Timestamp: 00 00 0E 10 -> 0x00000E10 = 3600 decimal
//   // Temp:      01 F4        -> 0x01F4 = 500 decimal => 5.00°C
//   const temperaturePacket = [
//     0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
//     0x00, 0x00, 0x0E, 0x10,
//     0x01, 0xF4
//   ];

//   const decoded = Decode(10, temperaturePacket);
//   console.log("Decoded Temperature:", JSON.stringify(decoded, null, 2));
// }
// // exampleUsage();

/*********************************************************
  EXPORTS (If using in Node.js)
*********************************************************/
module.exports = {
  Decode,
  TemperatureDataDecoder,
  HumidityDataDecoder,
  IMUDataDecoder,
  VibrationDataDecoder,
  DistanceDataDecoder
};
