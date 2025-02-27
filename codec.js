/************************************************************
  1) Utility: Parse JSON from the raw bytes
 ************************************************************/
  function parseJsonFromBytes(bytes) {
    // Convert array of bytes to ASCII text
    var text = String.fromCharCode.apply(null, bytes);
  
    // Attempt to parse JSON
    try {
      var obj = JSON.parse(text);
      return obj;
    } catch (err) {
      throw new Error("JSON parse error: " + err.message);
    }
  }
  
  /************************************************************
    2) Utility: Basic range checker
   ************************************************************/
  function validateRange(value, min, max, fieldName) {
    if (value < min || value > max) {
      throw new Error(fieldName + " out of range: " + value);
    }
  }
  
  /************************************************************
    3) TEMPERATURE DECODER
       Expects JSON fields: DevEUI, Timestamp, SensorType="TEMP", Value
   ************************************************************/
  class TemperatureDataDecoder {
    decode(jsonObj) {
      // Validate that Value is present
      if (typeof jsonObj.Value !== "number") {
        throw new Error("Missing numeric 'Value' for Temperature");
      }
  
      // OPTIONAL range check: -50..125 °C
      validateRange(jsonObj.Value, -50, 125, "Temperature");
  
      // Return a single-element SenML array
      return [
        {
          bn: `urn:dev:${jsonObj.DevEUI}:`,
          bt: jsonObj.Timestamp,       // epoch in seconds
          n: "temperature",
          u: "Cel",
          v: jsonObj.Value
        }
      ];
    }
  }
  
  /************************************************************
    4) HUMIDITY DECODER
       Expects JSON fields: DevEUI, Timestamp, SensorType="HUM", Value
   ************************************************************/
  class HumidityDataDecoder {
    decode(jsonObj) {
      if (typeof jsonObj.Value !== "number") {
        throw new Error("Missing numeric 'Value' for Humidity");
      }
  
      // OPTIONAL range check: 0..100 %RH
      validateRange(jsonObj.Value, 0, 100, "Humidity");
  
      return [
        {
          bn: `urn:dev:${jsonObj.DevEUI}:`,
          bt: jsonObj.Timestamp,
          n: "humidity",
          u: "%RH",
          v: jsonObj.Value
        }
      ];
    }
  }
  
  /************************************************************
    5) IMU DECODER
       Expects JSON fields: DevEUI, Timestamp, SensorType="IMU"
       with pitch, roll, yaw as separate numeric fields.
   ************************************************************/
  class IMUDataDecoder {
    decode(jsonObj) {
      // Validate each field
      if (typeof jsonObj.pitch !== "number" ||
          typeof jsonObj.roll  !== "number" ||
          typeof jsonObj.yaw   !== "number") {
        throw new Error("IMU requires numeric pitch, roll, yaw fields");
      }
  
      // OPTIONAL range checks: -180..180 degrees
      validateRange(jsonObj.pitch, -180, 180, "Pitch");
      validateRange(jsonObj.roll,  -180, 180, "Roll");
      validateRange(jsonObj.yaw,   -180, 180, "Yaw");
  
      // Return an array with 3 SenML objects
      return [
        {
          bn: `urn:dev:${jsonObj.DevEUI}:`,
          bt: jsonObj.Timestamp,
          n: "pitch",
          u: "deg",
          v: jsonObj.pitch
        },
        {
          bn: `urn:dev:${jsonObj.DevEUI}:`,
          bt: jsonObj.Timestamp,
          n: "roll",
          u: "deg",
          v: jsonObj.roll
        },
        {
          bn: `urn:dev:${jsonObj.DevEUI}:`,
          bt: jsonObj.Timestamp,
          n: "yaw",
          u: "deg",
          v: jsonObj.yaw
        }
      ];
    }
  }
  
  /************************************************************
    6) VIBRATION DECODER
       Expects JSON fields: DevEUI, Timestamp, SensorType="VIB", Value
   ************************************************************/
  class VibrationDataDecoder {
    decode(jsonObj) {
      if (typeof jsonObj.Value !== "number") {
        throw new Error("Missing numeric 'Value' for Vibration");
      }
  
      // OPTIONAL range check: 0..16 g
      validateRange(jsonObj.Value, 0, 16, "Vibration");
  
      return [
        {
          bn: `urn:dev:${jsonObj.DevEUI}:`,
          bt: jsonObj.Timestamp,
          n: "vibration",
          u: "g",
          v: jsonObj.Value
        }
      ];
    }
  }
  
  /************************************************************
    7) DISTANCE DECODER
       Expects JSON fields: DevEUI, Timestamp, SensorType="DIST", Value
   ************************************************************/
  class DistanceDataDecoder {
    decode(jsonObj) {
      if (typeof jsonObj.Value !== "number") {
        throw new Error("Missing numeric 'Value' for Distance");
      }
  
      // OPTIONAL range check: 0..100 m, for example
      validateRange(jsonObj.Value, 0, 100, "Distance");
  
      return [
        {
          bn: `urn:dev:${jsonObj.DevEUI}:`,
          bt: jsonObj.Timestamp,
          n: "distance",
          u: "m",
          v: jsonObj.Value
        }
      ];
    }
  }
  
  /************************************************************
    8) COMBINED Decode FUNCTION
       You can use this in ChirpStack or any other environment.
   ************************************************************/
  function Decode(fPort, bytes) {
    try {
      // 1) Parse JSON object from raw bytes
      var jsonObj = parseJsonFromBytes(bytes);
  
      // 2) Check the "SensorType" field
      if (!jsonObj.SensorType) {
        throw new Error("Missing 'SensorType' in JSON");
      }
  
      // 3) Instantiate decoders
      var tempDecoder = new TemperatureDataDecoder();
      var humDecoder  = new HumidityDataDecoder();
      var imuDecoder  = new IMUDataDecoder();
      var vibDecoder  = new VibrationDataDecoder();
      var distDecoder = new DistanceDataDecoder();
  
      // 4) Dispatch based on SensorType
      switch (jsonObj.SensorType) {
        case "TEMP":
          return tempDecoder.decode(jsonObj);
  
        case "HUM":
          return humDecoder.decode(jsonObj);
  
        case "IMU":
          return imuDecoder.decode(jsonObj);
  
        case "VIB":
          return vibDecoder.decode(jsonObj);
  
        case "DIST":
          return distDecoder.decode(jsonObj);
  
        default:
          throw new Error("Unknown SensorType: " + jsonObj.SensorType);
      }
    } catch (err) {
      return { error: err.message };
    }
  }
  
  /************************************************************
    9) DEMO USAGE (uncomment to test in Node.js or browser)
   ************************************************************/
  // function exampleUsage() {
  //   // Example Temperature JSON payload
  //   var textPayload = JSON.stringify({
  //     DevEUI: "1122334455667788",
  //     Timestamp: 1674816242,
  //     SensorType: "TEMP",
  //     Value: 25.42
  //   });
  
  //   // Convert to bytes (ASCII)
   //  var bytes = [];
  //   for (var i = 0; i < textPayload.length; i++) {
  //     bytes.push(textPayload.charCodeAt(i));
  //   }
  
  //   // Now decode
  //   var decoded = Decode(10, bytes); // fPort can be anything
  //   console.log("Decoded Data:", JSON.stringify(decoded, null, 2));
  // }
  // // exampleUsage();
  
  /************************************************************
    10) EXPORTS (Node.js usage, optional)
   ************************************************************/
  module.exports = {
    Decode,
    TemperatureDataDecoder,
    HumidityDataDecoder,
    IMUDataDecoder,
    VibrationDataDecoder,
    DistanceDataDecoder
  };