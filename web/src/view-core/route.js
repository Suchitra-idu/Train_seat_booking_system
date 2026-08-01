// L0 view-core: the fixed station list for the traveller app's From/To pickers. There is
// no `GET /stations` route (the timetable is per-trip, D22), so this mirrors
// config/timetable.json's station list on the backend; update both together if the route
// ever changes.

export const STATIONS = Object.freeze([
  { code: "FORT", name: "Colombo Fort" },
  { code: "RGM", name: "Ragama" },
  { code: "GPH", name: "Gampaha" },
  { code: "PLG", name: "Polgahawela" },
  { code: "KDY", name: "Kandy" },
  { code: "NWE", name: "Nawalapitiya" },
  { code: "HTN", name: "Hatton" },
  { code: "NNO", name: "Nanu Oya" },
  { code: "HPT", name: "Haputale" },
  { code: "ELA", name: "Ella" },
  { code: "BAD", name: "Badulla" },
]);
