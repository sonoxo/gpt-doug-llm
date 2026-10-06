export type EyerisLayer = {
  id: string;
  label: string;
  kind:
    | "weather"
    | "hazard"
    | "navigation"
    | "robot"
    | "traffic"
    | "aviation"
    | "maritime"
    | "authorized-sensor"
    | "synthetic";
  enabled: boolean;
  source: string;
  freshnessSeconds: number;
  privacyMode: "public" | "authorized" | "synthetic";
};

export const defaultEyerisLayers: EyerisLayer[] = [
  { id:"weather", label:"WEATHER", kind:"weather", enabled:true, source:"public", freshnessSeconds:300, privacyMode:"public" },
  { id:"hazards", label:"HAZARDS", kind:"hazard", enabled:true, source:"public/sim", freshnessSeconds:30, privacyMode:"public" },
  { id:"nav", label:"NAVIGATION", kind:"navigation", enabled:true, source:"operator", freshnessSeconds:1, privacyMode:"authorized" },
  { id:"robots", label:"ROBOTS", kind:"robot", enabled:true, source:"ROS2", freshnessSeconds:1, privacyMode:"authorized" },
  { id:"traffic", label:"TRAFFIC", kind:"traffic", enabled:false, source:"public", freshnessSeconds:60, privacyMode:"public" },
  { id:"aviation", label:"AVIATION", kind:"aviation", enabled:false, source:"public", freshnessSeconds:15, privacyMode:"public" },
  { id:"maritime", label:"MARITIME", kind:"maritime", enabled:false, source:"public", freshnessSeconds:60, privacyMode:"public" },
  { id:"sensors", label:"AUTHORIZED SENSORS", kind:"authorized-sensor", enabled:false, source:"user-owned", freshnessSeconds:1, privacyMode:"authorized" },
];
