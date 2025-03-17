/************************************************************
  1) Utility: Parse JSON from the raw bytes
 ************************************************************/
  function parseJsonFromBytes(bytes) {
    var text = String.fromCharCode.apply(null, bytes);
    try {
      return JSON.parse(text);
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
    3) Sensor Data Decoders
   ************************************************************/
  function TemperatureDataDecoder() {}
  TemperatureDataDecoder.prototype.decode = function (jsonObj) {
    if (typeof jsonObj.Value !== "number") {
      throw new Error("Missing numeric 'Value' for Temperature");
    }
    validateRange(jsonObj.Value, -50, 125, "Temperature");
    return [{ bn: "urn:dev:" + jsonObj.DevEUI + ":", bt: 1792200255, n: "temperature", u: "Cel", v: jsonObj.Value }];
  };
  
  function HumidityDataDecoder() {}
  HumidityDataDecoder.prototype.decode = function (jsonObj) {
    if (typeof jsonObj.Value !== "number") {
      throw new Error("Missing numeric 'Value' for Humidity");
    }
    validateRange(jsonObj.Value, 0, 100, "Humidity");
    return [{ bn: "urn:dev:" + jsonObj.DevEUI + ":", bt: 1792200255, n: "humidity", u: "%RH", v: jsonObj.Value }];
  };
  
  function IMUDataDecoder() {}
  IMUDataDecoder.prototype.decode = function (jsonObj, dev_eui) {
    // if (typeof jsonObj.pitch !== "number" || typeof jsonObj.roll !== "number" || typeof jsonObj.yaw !== "number") {
    //   throw new Error("IMU requires numeric pitch, roll, yaw fields");
    // }
    // validateRange(jsonObj.pitch, -180, 180, "Pitch");
    // validateRange(jsonObj.roll, -180, 180, "Roll");
    // validateRange(jsonObj.yaw, -180, 180, "Yaw");
    // return [
    //   { bn: "urn:dev:" + jsonObj.DevEUI + ":", bt: 1792200255, n: "pitch", u: "deg", v: jsonObj.pitch },
    //   { bn: "urn:dev:" + jsonObj.DevEUI + ":", bt: 1792200255, n: "roll", u: "deg", v: jsonObj.roll },
    //   { bn: "urn:dev:" + jsonObj.DevEUI + ":", bt: 1792200255, n: "yaw", u: "deg", v: jsonObj.yaw }
    // ];
    retObj = { data: [
      {bn: "urn:dev:" + dev_eui, n:"gx", u:"deg/sec", v:jsonObj.g[0]},
      {bn: "urn:dev:" + dev_eui, n:"gy", u:"deg/sec", v:jsonObj.g[1]},
      {bn: "urn:dev:" + dev_eui, n:"gz", u:"deg/sec", v:jsonObj.g[2]},
    ]};
    console.log(retObj);
    return retObj;
  };
  
  function VibrationDataDecoder() {}
  VibrationDataDecoder.prototype.decode = function (jsonObj) {
    if (typeof jsonObj.Value !== "number") {
      throw new Error("Missing numeric 'Value' for Vibration");
    }
    validateRange(jsonObj.Value, 0, 16, "Vibration");
    return [{ bn: "urn:dev:" + jsonObj.DevEUI + ":", bt: 1792200255, n: "vibration", u: "g", v: jsonObj.Value }];
  };
  
  function DistanceDataDecoder() {}
  DistanceDataDecoder.prototype.decode = function (jsonObj) {
    if (typeof jsonObj.Value !== "number") {
      throw new Error("Missing numeric 'Value' for Distance");
    }
    validateRange(jsonObj.Value, 0, 100, "Distance");
    return [{ bn: "urn:dev:" + jsonObj.DevEUI + ":", bt: 1792200255, n: "distance", u: "m", v: jsonObj.Value }];
  };
  
  /************************************************************
    4) COMBINED Decode FUNCTION
   ************************************************************/
  function Decode(bytes, dev_eui) {
    try {
      var jsonObj = parseJsonFromBytes(bytes);
      console.log(jsonObj)
      if (!jsonObj.fport) {
        throw new Error("Missing 'fport' in JSON");
      }
      var decoders = {
        "TEMP": new TemperatureDataDecoder(),
        "HUM": new HumidityDataDecoder(),
        3: new IMUDataDecoder(),
        "VIB": new VibrationDataDecoder(),
        4: new DistanceDataDecoder()
      };
      if (decoders[jsonObj.fport]) {
        return decoders[jsonObj.fport].decode(jsonObj, dev_eui);
      }
      throw new Error("Unknown SensorType: " + jsonObj.fport);
    } catch (err) {
      return { error: err.message };
    }
  }
  
  /************************************************************
    5) EXPORTS (Node.js usage, optional)
   ************************************************************/
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      Decode: Decode,
      TemperatureDataDecoder: TemperatureDataDecoder,
      HumidityDataDecoder: HumidityDataDecoder,
      IMUDataDecoder: IMUDataDecoder,
      VibrationDataDecoder: VibrationDataDecoder,
      DistanceDataDecoder: DistanceDataDecoder
    };
  }
  